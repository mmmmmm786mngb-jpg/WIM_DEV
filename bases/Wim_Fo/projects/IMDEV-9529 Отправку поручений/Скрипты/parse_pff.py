import re,sys,os,glob
sys.stdout.reconfigure(encoding='utf-8')
SRC=r'C:\1c\Cursor_1c\WORK\WIM_Fo\src\cf'
EXT=r'C:\1c\Claude_1C\TestProject\Wim_Fo\projects\IMDEV-9529 Отправку поручений\Расширения\FO_SendFixStub'
rec=re.compile(r'\{\n?\{"([^"]*)",\d+\},[^}]*\},"([^"]+)",(\d+),"((?:[^"]|"")*)",(\d+),([\d.eE+-]+),([\d.eE+-]+),([\d.eE+-]+),([\d.eE+-]+),(\d+),(\d+),(\d+)')
TYPE={'ОбщийМодуль':'CommonModules','РегистрСведений':'InformationRegisters','Обработка':'DataProcessors','Справочник':'Catalogs','Документ':'Documents','Перечисление':'Enums'}
KIND={'Модуль':'Module.bsl','МодульМенеджера':'ManagerModule.bsl','МодульОбъекта':'ObjectModule.bsl','МодульНабораЗаписей':'RecordSetModule.bsl'}
cache={}
def funcmap(mod, ext):
    key=(mod,ext)
    if key in cache: return cache[key]
    p=mod.split('.'); res=[]
    try:
        base = EXT if ext else SRC
        path=os.path.join(base,TYPE[p[0]],p[1],'Ext',KIND[p[-1]])
        cur='?'
        for i,l in enumerate(open(path,encoding='utf-8-sig'),1):
            m=re.match(r'\s*(?:Асинх\s+)?(Процедура|Функция)\s+([^\s(]+)',l)
            if m: cur=m.group(2)
            res.append(cur)
    except Exception as e: pass
    cache[key]=res; return res
def fn(mod,line,ext):
    m=funcmap(mod,ext)
    return m[line-1] if 0<line<=len(m) else '?'
def load(f):
    s=open(f,encoding='utf-8-sig').read()
    out=[]
    for e,mod,line,text,cnt,g,n,pg,pn,_,_,_ in rec.findall(s):
        ext=bool(e); line=int(line)
        out.append(dict(ext=e,mod=mod,line=line,text=text.replace('""','"'),cnt=int(cnt),g=float(g),n=float(n),fn=fn(mod,line,ext)))
    return out
