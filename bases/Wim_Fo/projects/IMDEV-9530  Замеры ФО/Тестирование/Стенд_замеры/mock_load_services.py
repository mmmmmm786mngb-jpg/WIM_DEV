# -*- coding: utf-8 -*-
"""Заглушки внешних источников обработок загрузок этапа 5 IMDEV-9530 на dev ФО.

Один процесс поднимает три сервиса:
- депозиты ДУ и ПИФ (веб-сервисы 1С, SOAP 1.2): http://127.0.0.1:18540/du?wsdl и /pif?wsdl, операция
  getDeposits(date) возвращает список deposit. Адреса задаются в настройках обработки депозитов (ВебСервисДУ, ВебСервисПИФ);
- котировки ММВБ (TIBCO, SOAP 1.1): http://amaptibco:8882/ - адрес задан в коде обработки, поэтому имя amaptibco
  на время теста направляется в hosts на 127.0.0.1. WSDL собирается из макета WSDL обработки (типы сервиса) с
  операцией StockPrice, у которой входное и выходное сообщение - Корень (обработка передает Корень и читает его же);
- индексы (MICROAPI, HTTP JSON): http://AMFLOW:8040/getIndexValue - адрес тоже в коде, AMFLOW направляется в hosts.

Ответы берутся из results/mock_load_rules.json (перечитывается на каждый запрос):
  {"du": [депозит, ...] | "fail", "pif": [...] | "fail",
   "quotes": {"docs": [{"exchange": "ММВБ", "day_offset": 0, "rows": [{"code", "currency", "close", "market2"}]}]} | "fail",
   "indexes": {"data": [{"index", "currency", "close", ...}], "composition": [{"index", "rows": [{"ticker", ...}]}]} | "fail"}
Дата документов котировок и данных индексов - DateFrom из запроса обработки. "fail" - SOAP Fault или HTTP 500.
Запросы пишутся в results/mock_load_requests.log.

    python mock_load_services.py
"""
import datetime
import glob
import json
import os
import re
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

HERE = os.path.dirname(os.path.abspath(__file__))
TASK = os.path.dirname(os.path.dirname(HERE))
RULES = os.path.join(HERE, "results", "mock_load_rules.json")
REQUESTS_LOG = os.path.join(HERE, "results", "mock_load_requests.log")
QUOTES_TEMPLATE = glob.glob(os.path.join(TASK, "ОРИГИНАЛЫ", "внЗагрузкаКотировокММВБ_epf", "*", "Templates", "WSDL",
                                         "Ext", "Template.bin"))[0]
DEPOSITS_PORT, QUOTES_PORT, INDEXES_PORT = 18540, 8882, 8040
DNS = "http://www.avancore.ru/deposits-test"


def write_log(line):
    os.makedirs(os.path.dirname(REQUESTS_LOG), exist_ok=True)
    with open(REQUESTS_LOG, "a", encoding="utf-8") as f:
        f.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M:%S} {line}\n")


def load_rules():
    if not os.path.exists(RULES):
        return {}
    with open(RULES, encoding="utf-8") as f:
        return json.load(f)


def esc(value):
    return str(value).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


class Base(BaseHTTPRequestHandler):
    def send_text(self, code, text, content_type):
        data = text.encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def body(self):
        return self.rfile.read(int(self.headers.get("Content-Length", 0))).decode("utf-8", errors="replace")

    def log_message(self, fmt, *args):
        pass


# ---------------------------------------------------------------- депозиты ДУ и ПИФ (SOAP 1.2, как веб-сервис 1С)

def deposits_wsdl(service):
    fields = [("id", "string"), ("name", "string"), ("marketvalue", "decimal"), ("day_interest", "decimal"),
              ("initialvalue", "decimal"), ("currentvalue", "decimal"), ("currency", "string"), ("datestart", "date"),
              ("datematurity", "date"), ("interest", "decimal")]
    elements = "".join(f'<xsd:element name="{n}" type="xsd:{t}"/>' for n, t in fields)
    elements += '<xsd:element name="agreements_prefix" type="xsd:string" minOccurs="0"/>'
    return f"""<?xml version="1.0" encoding="UTF-8"?>
<definitions xmlns="http://schemas.xmlsoap.org/wsdl/" xmlns:soap12bind="http://schemas.xmlsoap.org/wsdl/soap12/"
    xmlns:tns="{DNS}" xmlns:xsd="http://www.w3.org/2001/XMLSchema" name="{service.upper()}" targetNamespace="{DNS}">
  <types>
    <xsd:schema targetNamespace="{DNS}" elementFormDefault="qualified">
      <xsd:complexType name="Deposit"><xsd:sequence>{elements}</xsd:sequence></xsd:complexType>
      <xsd:complexType name="Deposits"><xsd:sequence>
        <xsd:element name="deposit" type="tns:Deposit" minOccurs="0" maxOccurs="unbounded"/>
      </xsd:sequence></xsd:complexType>
      <xsd:element name="getDeposits">
        <xsd:complexType><xsd:sequence><xsd:element name="date" type="xsd:dateTime"/></xsd:sequence></xsd:complexType>
      </xsd:element>
      <xsd:element name="getDepositsResponse">
        <xsd:complexType><xsd:sequence><xsd:element name="return" type="tns:Deposits"/></xsd:sequence></xsd:complexType>
      </xsd:element>
    </xsd:schema>
  </types>
  <message name="getDepositsRequestMessage"><part name="parameters" element="tns:getDeposits"/></message>
  <message name="getDepositsResponseMessage"><part name="parameters" element="tns:getDepositsResponse"/></message>
  <portType name="{service.upper()}PortType">
    <operation name="getDeposits">
      <input message="tns:getDepositsRequestMessage"/><output message="tns:getDepositsResponseMessage"/>
    </operation>
  </portType>
  <binding name="{service.upper()}Soap12Binding" type="tns:{service.upper()}PortType">
    <soap12bind:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
    <operation name="getDeposits">
      <soap12bind:operation style="document" soapAction="{DNS}#{service.upper()}:getDeposits"/>
      <input><soap12bind:body use="literal"/></input><output><soap12bind:body use="literal"/></output>
    </operation>
  </binding>
  <service name="{service.upper()}">
    <port name="{service.upper()}Soap12" binding="tns:{service.upper()}Soap12Binding">
      <soap12bind:address location="http://127.0.0.1:{DEPOSITS_PORT}/{service}"/>
    </port>
  </service>
</definitions>
"""


def soap12(body):
    return ('<?xml version="1.0" encoding="UTF-8"?><soap:Envelope xmlns:soap="http://www.w3.org/2003/05/soap-envelope">'
            f"<soap:Body>{body}</soap:Body></soap:Envelope>")


SOAP12_FAULT = soap12('<soap:Fault><soap:Code><soap:Value>soap:Receiver</soap:Value></soap:Code>'
                      '<soap:Reason><soap:Text xml:lang="ru">IMDEV-9530: тестовый отказ сервиса</soap:Text></soap:Reason>'
                      '</soap:Fault>')


class Deposits(Base):
    def service(self):
        return "pif" if self.path.lower().startswith("/pif") else "du"

    def do_GET(self):
        write_log(f"deposits GET {self.path}")
        self.send_text(200, deposits_wsdl(self.service()), "text/xml; charset=utf-8")

    def do_POST(self):
        service = self.service()
        self.body()
        rule = load_rules().get(service, [])
        if rule == "fail":
            write_log(f"deposits {service} getDeposits -> fault")
            self.send_text(500, SOAP12_FAULT, "application/soap+xml; charset=utf-8")
            return
        items = []
        for d in rule:
            parts = [f"<m:{k}>{esc(d[k])}</m:{k}>" for k in ("id", "name", "marketvalue", "day_interest", "initialvalue",
                                                            "currentvalue", "currency", "datestart", "datematurity",
                                                            "interest")]
            if d.get("agreements_prefix"):
                parts.append(f"<m:agreements_prefix>{esc(d['agreements_prefix'])}</m:agreements_prefix>")
            items.append("<m:deposit>" + "".join(parts) + "</m:deposit>")
        body = f'<m:getDepositsResponse xmlns:m="{DNS}"><m:return>{"".join(items)}</m:return></m:getDepositsResponse>'
        write_log(f"deposits {service} getDeposits -> {len(items)}")
        self.send_text(200, soap12(body), "application/soap+xml; charset=utf-8")


# ---------------------------------------------------------------- котировки ММВБ (TIBCO, SOAP 1.1)

def quotes_wsdl():
    with open(QUOTES_TEMPLATE, encoding="utf-8-sig") as f:
        text = f.read()
    # В обработке условие запроса заполняет NEED_DAY_SESSION, в макете WSDL этого поля нет.
    anchor = '<xs:element name="StockCode" type="xs:string" minOccurs="0"/>'
    assert text.count(anchor) == 1
    text = text.replace(anchor, anchor + '<xs:element name="NEED_DAY_SESSION" type="xs:boolean" minOccurs="0"/>')
    service = f"""
    <wsdl:portType name="QuotesPortType">
        <wsdl:operation name="StockPrice">
            <wsdl:input message="tns:Котировки"/>
            <wsdl:output message="tns:Котировки"/>
        </wsdl:operation>
    </wsdl:portType>
    <wsdl:binding name="QuotesBinding" type="tns:QuotesPortType">
        <soap:binding style="document" transport="http://schemas.xmlsoap.org/soap/http"/>
        <wsdl:operation name="StockPrice">
            <soap:operation style="document" soapAction="/StockPrice"/>
            <wsdl:input><soap:body use="literal" parts="data"/></wsdl:input>
            <wsdl:output><soap:body use="literal" parts="data"/></wsdl:output>
        </wsdl:operation>
    </wsdl:binding>
    <wsdl:service name="QuotesService">
        <wsdl:port name="QuotesPort" binding="tns:QuotesBinding">
            <soap:address location="http://amaptibco:{QUOTES_PORT}/StockPrice"/>
        </wsdl:port>
    </wsdl:service>
</wsdl:definitions>"""
    return text.replace("</wsdl:definitions>", service)


def soap11(body):
    return ('<?xml version="1.0" encoding="UTF-8"?>'
            '<SOAP-ENV:Envelope xmlns:SOAP-ENV="http://schemas.xmlsoap.org/soap/envelope/">'
            f"<SOAP-ENV:Body>{body}</SOAP-ENV:Body></SOAP-ENV:Envelope>")


SOAP11_FAULT = soap11('<SOAP-ENV:Fault><faultcode>SOAP-ENV:Server</faultcode>'
                      '<faultstring>IMDEV-9530: тестовый отказ сервиса</faultstring></SOAP-ENV:Fault>')


def shift(date_text, days):
    """Дата документа котировок со сдвигом от DateFrom запроса (сценарий с документами на две даты)."""
    if not days or not date_text:
        return date_text
    return (datetime.date.fromisoformat(date_text) + datetime.timedelta(days=days)).isoformat()


def tag(body, name):
    m = re.search(rf"<(?:\w+:)?{name}(?:\s[^>]*)?>(.*?)</(?:\w+:)?{name}>", body, re.S)
    return m.group(1).strip() if m else ""


class Quotes(Base):
    def do_GET(self):
        write_log(f"quotes GET {self.path}")
        self.send_text(200, quotes_wsdl(), "text/xml; charset=utf-8")

    def do_POST(self):
        body = self.body()
        date_from, date_to = tag(body, "DateFrom")[:10], tag(body, "DateTo")[:10]
        rule = load_rules().get("quotes", {"docs": []})
        if rule == "fail":
            write_log(f"quotes StockPrice {date_from}..{date_to} -> fault")
            self.send_text(500, SOAP11_FAULT, "text/xml; charset=utf-8")
            return
        docs, total = [], 0
        for doc in rule["docs"]:
            rows = []
            for r in doc["rows"]:
                rows.append(
                    "<ns0:СтрокаКотировок>"
                    f"<ns0:Допуск>{str(r.get('admit', True)).lower()}</ns0:Допуск>"
                    f"<ns0:Актив><ns1:КодЦБнаММВБ>{esc(r['code'])}</ns1:КодЦБнаММВБ></ns0:Актив>"
                    f"<ns0:ЦенаЗакрытия>{r['close']}</ns0:ЦенаЗакрытия>"
                    f"<ns0:РыночнаяЦена2>{r['market2']}</ns0:РыночнаяЦена2>"
                    f"<ns0:ВалютаКотировки><ns1:КодВалюты>{esc(r['currency'])}</ns1:КодВалюты>"
                    f"<ns1:Наименование>{esc(r['currency'])}</ns1:Наименование></ns0:ВалютаКотировки>"
                    "</ns0:СтрокаКотировок>")
            total += len(rows)
            docs.append("<ns0:ДокументКотировок>"
                        f"<ns0:Биржа><ns1:Наименование>{esc(doc['exchange'])}</ns1:Наименование></ns0:Биржа>"
                        f"<ns0:Дата>{shift(date_from, doc.get('day_offset', 0))}</ns0:Дата>"
                        f"<ns0:Состав>{''.join(rows)}</ns0:Состав>"
                        "</ns0:ДокументКотировок>")
        root = ('<ns0:Корень xmlns:ns0="http://www.avancore.ru/quotes" xmlns:ns1="http://www.avancore.ru/securities">'
                f"<ns0:УсловиеКотировок><ns0:DateFrom>{date_from}</ns0:DateFrom><ns0:DateTo>{date_to}</ns0:DateTo>"
                "</ns0:УсловиеКотировок>" + "".join(docs) + "</ns0:Корень>")
        write_log(f"quotes StockPrice {date_from}..{date_to} -> документов {len(docs)}, строк {total}")
        self.send_text(200, soap11(root), "text/xml; charset=utf-8")


# ---------------------------------------------------------------- индексы (MICROAPI, HTTP JSON)

class Indexes(Base):
    def do_POST(self):
        request = json.loads(self.body() or "{}")
        date = str(request.get("DateFrom", ""))[:10] + "T00:00:00"
        rule = load_rules().get("indexes", {"data": [], "composition": []})
        if rule == "fail":
            write_log(f"indexes {self.path} {request} -> 500")
            self.send_text(500, '{"error": "IMDEV-9530: тестовый отказ сервиса"}', "application/json; charset=utf-8")
            return
        data = [{"IndexDate": date, "Index": d["index"], "Currency": d["currency"], "Open": str(d["open"]),
                 "Maximum": str(d["max"]), "Minimum": str(d["min"]), "Close": str(d["close"]),
                 "Volume": str(d["volume"]), "Duration": str(d.get("duration", 0)), "Yield": str(d.get("yield", 0))}
                for d in rule["data"]]
        composition = [{"Index": c["index"], "IndexDate": date,
                        "IndexStructure": [{"Ticker": r["ticker"], "Weight": str(r["weight"]),
                                            "FreeFloat": str(r.get("freefloat", 1)), "CoeffWeight": str(r.get("coeff", 1)),
                                            "EmissionVolume": str(r.get("emission", 0)), "Qo": str(r.get("qo", 0)),
                                            "Capitalization": str(r.get("cap", 0))} for r in c["rows"]]}
                       for c in rule["composition"]]
        write_log(f"indexes {self.path} {request.get('Indexes')} -> данных {len(data)}, составов {len(composition)}")
        self.send_text(200, json.dumps({"IndexData": data, "IndexComposition": composition}, ensure_ascii=False),
                       "application/json; charset=utf-8")


def main():
    sys.stdout.reconfigure(encoding="utf-8")
    servers = [ThreadingHTTPServer(("127.0.0.1", DEPOSITS_PORT), Deposits),
               ThreadingHTTPServer(("127.0.0.1", QUOTES_PORT), Quotes),
               ThreadingHTTPServer(("127.0.0.1", INDEXES_PORT), Indexes)]
    for server in servers[1:]:
        threading.Thread(target=server.serve_forever, daemon=True).start()
    print(f"Заглушки загрузок: депозиты :{DEPOSITS_PORT}/du|pif, котировки amaptibco:{QUOTES_PORT}, "
          f"индексы AMFLOW:{INDEXES_PORT}", flush=True)
    servers[0].serve_forever()


if __name__ == "__main__":
    main()
