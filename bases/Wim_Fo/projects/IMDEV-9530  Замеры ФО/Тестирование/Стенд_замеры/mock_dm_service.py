# -*- coding: utf-8 -*-
"""Заглушка веб-сервиса 1С:ДО (DMService) для теста обработки «Загрузка неторговых поручений РОСТ» на dev ФО (IMDEV-9530).

Обработка вызывает GetAgreementAmount(НомерДоговора) и ждет строку JSON {"Сумма": N, "ОтправленоНаБрокерский": Булево}.
Ответ по номеру договора берется из results/mock_dm_rules.json: {"<номер договора>": {"Сумма": N,
"ОтправленоНаБрокерский": true} | "fail"}; "fail" - SOAP Fault (в обработке это исключение вызова сервиса). Договоры
вне файла получают сумму 0. Файл перечитывается на каждый запрос, запросы пишутся в results/mock_dm_requests.log.

    python mock_dm_service.py            слушает http://127.0.0.1:18530/dm (WSDL - http://127.0.0.1:18530/dm?wsdl)
"""
import datetime
import json
import os
import re
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
RULES = os.path.join(HERE, "results", "mock_dm_rules.json")
REQUESTS_LOG = os.path.join(HERE, "results", "mock_dm_requests.log")
HOST, PORT = "127.0.0.1", 18530
NS = "http://www.1c.ru/dm"

WSDL = f"""<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://schemas.xmlsoap.org/wsdl/" xmlns:soap12bind="http://schemas.xmlsoap.org/wsdl/soap12/"
    xmlns:tns="{NS}" xmlns:xsd="http://www.w3.org/2001/XMLSchema" name="DMService" targetNamespace="{NS}">
  <types>
    <xsd:schema targetNamespace="{NS}" elementFormDefault="qualified">
      <xsd:element name="GetAgreementAmount">
        <xsd:complexType><xsd:sequence><xsd:element name="AgreementNumber" type="xsd:string"/></xsd:sequence></xsd:complexType>
      </xsd:element>
      <xsd:element name="GetAgreementAmountResponse">
        <xsd:complexType><xsd:sequence><xsd:element name="return" type="xsd:string"/></xsd:sequence></xsd:complexType>
      </xsd:element>
      <xsd:element name="GetClosingRetailAgreements">
        <xsd:complexType><xsd:sequence/></xsd:complexType>
      </xsd:element>
      <xsd:element name="GetClosingRetailAgreementsResponse">
        <xsd:complexType><xsd:sequence><xsd:element name="return" type="xsd:string"/></xsd:sequence></xsd:complexType>
      </xsd:element>
    </xsd:schema>
  </types>
  <message name="GetAgreementAmountRequestMessage"><part name="parameters" element="tns:GetAgreementAmount"/></message>
  <message name="GetAgreementAmountResponseMessage"><part name="parameters" element="tns:GetAgreementAmountResponse"/></message>
  <message name="GetClosingRetailAgreementsRequestMessage"><part name="parameters" element="tns:GetClosingRetailAgreements"/></message>
  <message name="GetClosingRetailAgreementsResponseMessage"><part name="parameters" element="tns:GetClosingRetailAgreementsResponse"/></message>
  <portType name="DMServicePortType">
    <operation name="GetAgreementAmount">
      <input message="tns:GetAgreementAmountRequestMessage"/><output message="tns:GetAgreementAmountResponseMessage"/>
    </operation>
    <operation name="GetClosingRetailAgreements">
      <input message="tns:GetClosingRetailAgreementsRequestMessage"/><output message="tns:GetClosingRetailAgreementsResponseMessage"/>
    </operation>
  </portType>
  <binding name="DMServiceSoap12Binding" type="tns:DMServicePortType">
    <soap12bind:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
    <operation name="GetAgreementAmount">
      <soap12bind:operation style="document" soapAction="{NS}#DMService:GetAgreementAmount"/>
      <input><soap12bind:body use="literal"/></input><output><soap12bind:body use="literal"/></output>
    </operation>
    <operation name="GetClosingRetailAgreements">
      <soap12bind:operation style="document" soapAction="{NS}#DMService:GetClosingRetailAgreements"/>
      <input><soap12bind:body use="literal"/></input><output><soap12bind:body use="literal"/></output>
    </operation>
  </binding>
  <service name="DMService">
    <port name="DMServiceSoap12" binding="tns:DMServiceSoap12Binding">
      <soap12bind:address location="http://{HOST}:{PORT}/dm"/>
    </port>
  </service>
</definitions>
"""


def envelope(body):
    return ('<?xml version="1.0" encoding="UTF-8"?><soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">'
            f"<soap:Body>{body}</soap:Body></soap:Envelope>")


def response(operation, value):
    escaped = value.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    return envelope(f'<m:{operation}Response xmlns:m="{NS}"><m:return>{escaped}</m:return></m:{operation}Response>')


FAULT = envelope('<soap:Fault><soap:Code><soap:Value>soap:Receiver</soap:Value></soap:Code>'
                 '<soap:Reason><soap:Text xml:lang="ru">IMDEV-9530: тестовый отказ сервиса</soap:Text></soap:Reason>'
                 '</soap:Fault>')


def load_rules():
    if not os.path.exists(RULES):
        return {}
    with open(RULES, encoding="utf-8") as f:
        return json.load(f)


def write_log(line):
    os.makedirs(os.path.dirname(REQUESTS_LOG), exist_ok=True)
    with open(REQUESTS_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {line}\n")


class Handler(BaseHTTPRequestHandler):
    def _send(self, code, text, content_type):
        data = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):
        write_log(f"GET {self.path}")
        self._send(200, WSDL, "text/xml; charset=utf-8")

    def do_POST(self):
        body = self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8", errors="replace")
        if "GetClosingRetailAgreements" in body:
            write_log("GetClosingRetailAgreements -> ''")
            self._send(200, response("GetClosingRetailAgreements", ""), "application/soap+xml; charset=utf-8")
            return
        match = re.search(r"<(?:\w+:)?AgreementNumber(?:\s[^>]*)?>(.*?)</(?:\w+:)?AgreementNumber>", body, re.S)
        number = match.group(1).strip() if match else ""
        if not number:
            write_log("тело запроса без номера договора: " + " ".join(body[:800].split()))
        rule = load_rules().get(number, {"Сумма": 0, "ОтправленоНаБрокерский": False})
        if rule == "fail":
            write_log(f"GetAgreementAmount {number} -> fault")
            self._send(500, FAULT, "application/soap+xml; charset=utf-8")
            return
        answer = json.dumps({"НомерДУ": number, **rule}, ensure_ascii=False)
        write_log(f"GetAgreementAmount {number} -> {answer}")
        self._send(200, response("GetAgreementAmount", answer), "application/soap+xml; charset=utf-8")

    def log_message(self, fmt, *args):
        pass


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Заглушка DMService: http://{HOST}:{PORT}/dm?wsdl", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
