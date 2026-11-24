"""Build a brand's CPS LDR dashboard from the Hero dashboard (the master format).

    python make_brand.py bgauss  <hero index.html> <out index.html>
    python make_brand.py ampere  <hero index.html> <out index.html>

Everything stays as in Hero (tabs, filters, exports, roles, admin panel, sheet guard). Per brand it changes: names,
lead-master tab + months, the Process value in the retail sheet, the first lead month, model families (Retail
Dispersion / targets), the users / invites / presence collections. Hero-only inputs are left empty and the tabs say so:
the non-scope retail sheet (Hero dealer-system export) and the AO x model targets. Zone falls back to the lead's state
(Hero's own state -> zone map) because only Hero's lead tab has a Region column.
Re-run after every change to the Hero page so the brands stay in step with it.
"""
import json, re, sys

WORKBOOKS = {  # one lead-master workbook per month (same ids for every brand; each brand has its own tab)
    "Apr'2026": "1ApNKQtNvPJ0H9WVAgqLU8jBozEl5K1zn-vCY0iaEi_g", "May'2026": "1jnhdvPUEefW7HrD44ffvH2k3v0eUe2JGolXkX6EIKbQ",
    "Jun'2026": "1qAvzs6ucsPtk3joTsYeHijk2Tx_JRcCBsXzKDbnEOPc", "Jul'2026": "1t29vI-JdKu7HDaaLX33N3wFnhylFLbOkwPhyWc6ZKiA",
    "Aug'2026": "18oNdrfWNJjZkpBRe3dsoj8r-auOVeZyad9dbJ1lIMAo", "Sep'2026": "1tkvHOk6S3tdl1Mdzcfi1b5B8yeyIcWXtKs3jmiVroDM",
    "Oct'2026": "1WgyRvNW02UxCYyhQDLfaFa86RciciSeGXeQmBF7ymIg", "Nov'2026": "1MdlYzXsJ1rAZ1PfVDNXE7n8IGaHQuoW25QHh3tq6XRc"}
MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]

BRANDS = {
    "bgauss": dict(name="BGauss", full="BGauss (RR Global)", proc="bgauss", gid="1550993047", start="Apr'2026",
                   prefix="bgauss",
                   families={"BGauss Max C12": "BGauss Max C12 Family", "BGauss C12 MaxR": "BGauss Max C12 Family",
                             "BGauss RUV 350": "BGauss RUV 350", "BGauss OoWah": "BGauss OoWah"},
                   canon_purchased={}),
    "ampere": dict(name="Ampere", full="Ampere (Greaves Electric Mobility)", proc="ampere", gid="0", start="Sep'2026",
                   prefix="ampere",
                   families={"Ampere Magnus G Max": "Ampere Magnus Family", "Ampere Magnus Neo": "Ampere Magnus Family",
                             "Ampere Magnus Grand": "Ampere Magnus Family", "Ampere Nexus": "Ampere Nexus",
                             "Ampere Reo": "Ampere Reo"},
                   canon_purchased={"New Ampere Magnus Neo": "Ampere Magnus Neo"}),
}

key, src, dst = sys.argv[1], sys.argv[2], sys.argv[3]
B = BRANDS[key]
NL, CR = chr(10), chr(13)
raw = open(src, encoding="utf-8", newline="").read()
crlf = (CR + NL) in raw
s = raw.replace(CR + NL, NL)


def rep(old, new, n=1):
    global s
    assert s.count(old) == n, (s.count(old), old[:90])
    s = s.replace(old, new)


def sub(pat, new, n=1, flags=0):
    global s
    s, k = re.subn(pat, new, s, flags=flags)
    assert k == n, (k, pat[:90])


def mi(m):  # "Apr'2026" -> (2026, 3)
    return int(m[4:]), MONTHS.index(m[:3])


y0, m0 = mi(B["start"])
months = [m for m in WORKBOOKS if mi(m) >= (y0, m0)]
nxt = f"{MONTHS[(m0 + 1) % 12]}'{y0 + (m0 + 1) // 12}"
js = lambda v: json.dumps(v, ensure_ascii=False)

# names
rep("<title>Hero Lead Disposition Dashboard v2.0</title>", f"<title>{B['name']} Lead Disposition Dashboard v2.0</title>")
rep("'Hero MotoCorp'", js(B["full"]), 2)
rep("'Hero CPS'", js(B["name"] + " CPS"))
s = s.replace("Hero MotoCorp LDR", B["name"] + " LDR")   # code comments
s = re.sub(r"([`'])Hero_", lambda m: m.group(1) + B["name"] + "_", s)

# lead masters + retail sheet
a = s.index("const HERO_LEAD_MASTER_BY_MONTH = {"); b = s.index("};", a) + 2
s = s[:a] + ("const HERO_LEAD_MASTER_BY_MONTH = {   // " + B["name"] + " tab (gid " + B["gid"] + ") of each monthly lead master\n"
             + "".join(f'  "{m}": "https://docs.google.com/spreadsheets/d/{WORKBOOKS[m]}/edit?gid={B["gid"]}#gid={B["gid"]}",\n' for m in months)
             + "};") + s[b:]
sub(r'NON_SCOPE_RETAIL_URL: "[^"]*",', 'NON_SCOPE_RETAIL_URL: "",   // Hero-only (Hero dealer-system export)')
rep("        fetchSheetCsv(HERO_SHEETS_CONFIG.NON_SCOPE_RETAIL_URL,true),",
    "        HERO_SHEETS_CONFIG.NON_SCOPE_RETAIL_URL?fetchSheetCsv(HERO_SHEETS_CONFIG.NON_SCOPE_RETAIL_URL,true):Promise.resolve(''),")
rep("    const isHeroBrand=!proc||procLow==='hero'||procLow.startsWith('hero');",
    f"    const isHeroBrand=procLow==={js(B['proc'])};   // retail sheet column 'Process' = {B['name']}")

# first lead month (Hero: 3 Aug 2026)
rep("const DATA_CUTOFF=new Date(2026,7,3);", f"const DATA_CUTOFF=new Date({y0},{m0},1);")
rep("const CUTOFF_MONTH_ORDER_CLEAR=heroMonthOrder(\"Sep'2026\");", f"const CUTOFF_MONTH_ORDER_CLEAR=heroMonthOrder({js(nxt)});")
rep("    const augOrd=heroMonthOrder(\"Aug'2026\");", f"    const augOrd=heroMonthOrder({js(B['start'])});")
# Hero starts mid-month (3 Aug), so its first month needs a readable day; a brand starting on the 1st does not (and
# some brand sheets write dates as "2026-Sep-12", which that check cannot read - Ampere lost 688 Sep leads to it)
rep("    if(lmo===augOrd){", "    if(lmo===augOrd&&DATA_CUTOFF.getDate()>1){")

# quarters (Indian FY: Q1 Apr-Jun ... Q4 Jan-Mar) and the per-month target divisor (active months in that quarter)
def quarter(y, m):
    return ("Q1", "Q2", "Q3", "Q4")[((m - 3) % 12) // 3]
qm, cfg = {}, {}
for k in range(12):
    y, m = y0 + (m0 + k) // 12, (m0 + k) % 12
    if (y, m) > (2027, 2):          # through Mar'2027 (end of FY 2026-27)
        break
    qm.setdefault(quarter(y, m), []).append(f"{MONTHS[m]}'{y}")
for q, ms in qm.items():
    for m in ms:
        cfg[m] = {"q": q, "div": len(ms)}
a = s.index("const HERO_Q_MONTHS = {"); b = s.index("};", a) + 2
s = s[:a] + "const HERO_Q_MONTHS = {\n" + "".join(f"  {q}: new Set({js(ms)}),\n" for q, ms in qm.items()) + "};" + s[b:]
a = s.index("const HERO_MONTH_TARGET_CFG = {"); b = s.index("};", a) + 2
s = s[:a] + "const HERO_MONTH_TARGET_CFG = {\n" + "".join(f"  {js(m)}: {{ q:'{c['q']}', div:{c['div']} }},\n" for m, c in cfg.items()) + "};" + s[b:]

# targets: none yet (Hero's are AO x model x quarter from Hero's plan)
sub(r"const HERO_TARGET_DATA=\{.*?\};\n", f"const HERO_TARGET_DATA={{}};   // {B['name']} targets: AO/region -> model -> quarter -> [leads, retails, ...] as in Hero\n", flags=re.S)
a = s.index("const HERO_TD_MODEL_MAP = new Map(["); b = s.index("]);", a) + 3
s = s[:a] + "const HERO_TD_MODEL_MAP = new Map([\n" + "".join(f"  [{js(k.lower())}, {js(v)}],\n" for k, v in B["families"].items()) + "]);" + s[b:]

# model families for Retail Dispersion; a model with no family is its own family (Hero: unmapped = always CROSS)
for name in ("DISP_PM_CAT", "DISP_LM_CAT"):
    a = s.index(f"const {name} = {{"); b = s.index("};", a) + 2
    s = s[:a] + f"const {name} = {{\n" + "".join(f"  {js(k)}:{js(v)},\n" for k, v in B["families"].items()) + "};" + s[b:]
rep("      const lmCat  = DISP_LM_CAT[maps.mdl[mi]];",
    "      const lmCat  = DISP_LM_CAT[maps.mdl[mi]] !== undefined ? DISP_LM_CAT[maps.mdl[mi]] : maps.mdl[mi];")
a = s.index("const _HERO_PUR_MDL_CANONICAL = {"); b = s.index("};", a) + 2
s = s[:a] + "const _HERO_PUR_MDL_CANONICAL = {\n" + "".join(f"  {js(k)}:{js(v)},\n" for k, v in B["canon_purchased"].items()) + "};" + s[b:]
rep("function normMdl(s){return(s||'').toLowerCase().replace(/^hero\\s+/,'')",
    "function normMdl(s){return(s||'').toLowerCase().replace(/^" + B["proc"] + "\\s+/,'')")

# zone: Hero's lead tab has Region; the others take the zone from the state
rep("      ao:ao||'',region:region||'',\n      lead_month,leadDate",
    "      ao:ao||'',region:region||getZone(canonicalState(state)),\n      lead_month,leadDate")

# own access lists on the shared Firebase project
rep("var USERS_COL='hero_users';", f"var USERS_COL='{B['prefix']}_users';")
rep("var INVITED_COL='hero_invited_emails';", f"var INVITED_COL='{B['prefix']}_invited_emails';")
rep("var PRESENCE_PATH='hero_presence';", f"var PRESENCE_PATH='{B['prefix']}_presence';")

for bad in ("Hero MotoCorp", "'hero_users'", "hero_presence", "procLow==='hero'", "1691488845", "gid=1299063631"):
    assert bad not in s, bad
open(dst, "w", encoding="utf-8", newline="").write(s.replace(NL, CR + NL) if crlf else s)
print(f"built {B['name']}: months {months[0]}..{months[-1]} ({len(months)}), quarters {list(qm)}, -> {dst}")
