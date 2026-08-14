"""Extrae las palabras más frecuentes del texto visible (JSX) de los componentes."""
import re
import collections
import glob

# Palabras inglesas/técnicas frecuentes que no deben considerarse "español del UI"
en_words = set("""
class function const return import export null true false async await string number
undefined this props state set use from when type item items data id code status name
text left right top bottom center flex grid gap min max auto px html svg json api http
url icon error role tab aria label color dark light theme size sm md lg xl font bold
medium base default primary secondary destructive outline ghost link submit button key
value ref form page app main nav header footer section list map filter find index length
push join split slice date time now today month day year week hour minute second total
price cost email phone address city state country logo upload file message response
request result rows columns width height offset align justify wrap basis grow shrink
hidden visible absolute relative static fixed sticky zindex opacity blur ring shadow
border rounded download disabled enabled readonly checked selected required optional
first last next previous prev back forward save cancel delete edit add remove create
update search sort order view show hide open close print export import send receive
approve reject accept deny confirm sign verify login logout register submit reset clear
apply start stop pause resume play done ready loading success failed warning info help
support about contact home dashboard settings config profile account admin user users
company companies client clients product products service services invoice invoices
proforma proformas receipt receipts payment payments report reports chart charts table
tables form forms modal dialog badge card cards tabs tab accordion tooltip toast menu
dropdown sidebar container wrapper content grid column columns span row rows cell cells
group groups section sections block blocks title titles subtitle description desc
placeholder hint note notice alert sheet drawer popover command skeleton separator
aspect avatar button checkbox collapsible combobox contextmenu hovercard menubar
navigation pagination progress radio scrollarea select slider switch textarea toggle
toolbar breadcrumb calendar carousel input output display block inline inherit none
solid dashed dotted double wavy thin thick normal italic oblique underline overline
line style weight family variant case transform object fit cover contain fill position
overflow scroll clip visible resize ratio stroke cap join miter round bevel square
butt vertical horizontal diagonal radial linear gradient color rgb rgba hsl hsla hex
red green blue yellow orange purple pink gray grey black white transparent current
initial revert unset accent background border box content cursor pointer grab move
wait write cell crosshair zoom pin ns ew nesw nwse col row all preview export link
scrollbar overscroll behavior touch pan pinch wheel ms webkit moz o khtml caret
user drag drop paste copy cut select whole word character spelling grammar textarea
column fill flexbox media query mask clip path paint order isolation mix blend mode
backface perspective rotate skew scale translate matrix origin repeat no repeat
space around evenly between stretch baseline start end flexstart flexend
""".split())

brands = set("""
contaec contacc tym tymm technology react next typescript javascript tailwind css
node npm python fastapi sqlalchemy postgres redis docker git github whatsapp web
sistema software plataforma version app
""".split())

# Acrónimos / siglas que no se traducen
acronyms = set("""
ruc sri iva ice iess rimpe pos crm erp xml pdf xls csv api url id uuid dni nif
nit nss otp tfa sso ldap oauth smtp pop imap ftp ssh ssl tls http https dns ip
lan wan vpn usb lcd led oled cpu gpu ram rom ssd hdd bios os ios android windows
mac linux ubuntu debian centos fedora arch kali ubuntu debian
""".split())

stop = en_words | brands | acronyms

freq = collections.Counter()
for f in glob.glob('src/components/contaec-*.tsx'):
    src = open(f, encoding='utf-8').read()
    chunks = re.findall(r'>([^<>{}]{2,80})<', src)
    for c in chunks:
        c = re.sub(r'\{[^}]*\}', ' ', c)
        for w in re.findall(r'[A-Za-zÁÉÍÓÚÜÑáéíóúüñ]{4,}', c):
            freq[w.lower()] += 1

# Solo palabras con acentos o que no están en el stoplist inglés
candidates = [(w, c) for w, c in freq.items() if w not in stop and c >= 2]
candidates.sort(key=lambda x: -x[1])

print("=== Top 400 palabras candidatas (español del UI) ===")
for i, (w, c) in enumerate(candidates[:400]):
    print(f"{w}:{c}", end="  ")
    if (i + 1) % 5 == 0:
        print()
