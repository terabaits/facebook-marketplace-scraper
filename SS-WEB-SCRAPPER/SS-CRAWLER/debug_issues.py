# -*- coding: utf-8 -*-
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
sys.path.insert(0, 'src')

from src.utils.text import normalize_text, extract_cpu_tokens

# Test text from pbdhn.html
text1 = """Sveiki, pārdodu labu, ātru un jaudīgu datoru. Dators izmantots 2 gadus - gan darbam, gan spēlēm. Nav ne reizi "crashojis". Strādāja ļoti labi un bez problēmām, mierīgi pavelk dažāda satura spēles.

Pārdodu, jo tik bieži vairs nesanāk būt mājās, kā arī nevēlos, lai krāj putekļus ;)

Komponentes:

 CPU - AMD R5 1600 3.2 GHz

 GPU - NVIDIA GeForce GTX 1060 6GB

 RAM - 2 x 4GB Viper Steel gaming DDR4 3200Mhz

 MB - B450 Aorus Elite

 PSU - 500W EcoSeries

 Storage - Crucial BX500 SAT 6gb/s 480GB SSD

 Cooling - 5 RF120M RGB Fans

Un komplektā nāk vēl:

 Monitors - UltraGear 24GN600 144Hz 1ms (ideālā stāvoklī bez švīkām vai darbības traucējumiem)

 Klaviatūra - Royal Kludge RK84 red switch

Par vairāk jautājumiem droši rakstat.

 Procesors:

 Amd r5 1600

 Procesora frekvence, Ghz:

 3.20

 Pamat plate:

 B450 aorus elite

 Video:

 Nvidia gtx 1060

 Operatīvā atmiņa, Gb:

 8

 HDD apjoms, Gb:

 480

 DVD:

 -

 Stāvoklis:

 lietota

 Cena:

 365 €

 Foto:

	https://i.ss.com/gallery/8/1452/362792/electronics-computers-pc-72558382.800.jpg

https://i.ss.com/gallery/8/1452/362792/electronics-computers-pc-72558383.800.jpg

https://i.ss.com/gallery/8/1452/362792/electronics-computers-pc-72558384.800.jpg

https://i.ss.com/gallery/8/1452/362792/electronics-computers-pc-72558385.800.jpg

https://i.ss.com/gallery/8/1495/373529/electronics-computers-pc-74705772.800.jpg

 Tālrunis:

 (+371)25-41-***

 Visi sludinājumi ar šo tālruni

	E-mail:
	Nosūtīt e-pastuVisi sludinājumi ar šo E-mail adresi

Vieta:Rīgas rajons"""

print("=== pbdhn.html Analysis ===")
normalized = normalize_text(text1)
print(f"Normalized: {normalized[:200]}...")
print()

# Check for 5160
print(f"'5160' in normalized: {'5160' in normalized}")

# Extract CPU tokens
tokens = extract_cpu_tokens(text1)
print(f"CPU tokens: {tokens}")
print()

# Check Ryzen patterns
import re
tryzen_matches = re.findall(r'ryzen\s*\d?\s*\d{3,4}', normalized)
print(f"Ryzen matches: {tryzen_matches}")
print()

print("=== pcneb.html Analysis ===")
text2 = """Pārdodu strādājošu datoru labā tehniskā stāvoklī. Piemērots spēlēm, darbam, mācībām un ikdienas lietošanai. Windows 10 uzinstalēts, gatavs lietošanai.

Cpu: intel core i5-6500, 3.5 ghz

mb: asus h110m-r

ram: 4 gb ddr4 2133 mhz (1x)

gpu: nvidia geforce gtx 1660, 6 gb

ssd: netac 256gb

psu: deepcool pf500 ar čeku

Ja interesē, varu pievienot divus lietotus HDD (500 GB un 320 GB). Nav ideālā stāvoklī, bet var noderēt kā bonuss.

Rakstīt SMS vai WhatsApp.

 Procesors:

 I5 6500

 Procesora frekvence, Ghz:

 3.20

 Pamat plate:

 Asus h110m-r

 Video:

 Gtx 1660 6gb oc

 Operatīvā atmiņa, Gb:

 4

 HDD apjoms, Gb:

 500

 DVD:

 -

 Stāvoklis:

 lietota

 Cena:

 180 €"""

normalized2 = normalize_text(text2)
print(f"'i56500' in normalized: {'i56500' in normalized2}")
print(f"'i56500te' in normalized: {'i56500te' in normalized2}")

# Extract tokens
tokens2 = extract_cpu_tokens(text2)
print(f"CPU tokens: {tokens2}")
print()

print("=== lphjf.html Analysis ===")
text3 = """Ryzen 7 8700f, Rx6800Xt 16gb, 2tb ssd, 32gb ddr5, jaudīgs dators - perfekts jaunākajām datorspēlēm un ikdienai. Iespējams iegādāties bez videokartes.

- Datoram ir jauns korpuss, cpu, ūdensdzese, operatīvā atmiņa, ssd disks. Garantija mēnesis visam datoram.

- Ideāls datorspēlēm RX6800XT videokarti.

- Perfekti salikts, kluss un kvalitatīvs.

- Pie iegādes iespējams notestēt un pārliecināties par datora darbību. Atrodas centrā.

Komponentes/составные части:

Procesors: AMD Ryzen r7 8700f - jauns;

Mātesplate: MSI B650 Tomahawk WIFI - lietota;

Operatīvā atmiņa: ddr5 samsung 2x16 laptop ram ar adapteriem 5200mhz.

Cietie diski: Kinsgotn NV2 Pcie 4.0 2tb m. 2 ssd - jauns;

Videokarte: Powercolor red devil RX6800XT 16gb - lietota;

Barības bloks: CoolerMaster V1200 1200W 80+Platinum - lietots;

Korpuss: BeQuiet. 802 window - jauns;

Dzesētājs: Arctic 360mm LiquidFreezer iii - jauns;

Operētājsistēma: Microsoft Windows 11 Professional;

 Procesors:

 R7 8700f

 Procesora frekvence, Ghz:

 5.00

 Pamat plate:

 B650 tomahawk wifi

 Video:

 Rx6800xt

 Operatīvā atmiņa, Gb:

 32

 HDD apjoms, Gb:

 2048

 DVD:

 -

 Stāvoklis:

 lietota

 Cena:

 1 199 €"""

normalized3 = normalize_text(text3)
print(f"Normalized: {normalized3[:300]}...")
print()

# Check for 8700f vs 8700g vs 8700
print(f"'8700f' in normalized: {'8700f' in normalized3}")
print(f"'8700g' in normalized: {'8700g' in normalized3}")
print(f"'8700' in normalized: {'8700' in normalized3}")
print(f"'r78700f' in normalized: {'r78700f' in normalized3}")

# Extract CPU tokens
tokens3 = extract_cpu_tokens(text3)
print(f"CPU tokens: {tokens3}")

# GPU check
print(f"\n'rx6800xt' in normalized: {'rx6800xt' in normalized3}")
print(f"'6800xt' in normalized: {'6800xt' in normalized3}")
print(f"'6800' in normalized: {'6800' in normalized3}")

# SSD check  
print(f"\n'nv2' in normalized: {'nv2' in normalized3}")
print(f"'kinsgotn' in normalized: {'kinsgotn' in normalized3}")
print(f"'kingston' in normalized: {'kingston' in normalized3}")
print(f"'860evo' in normalized: {'860evo' in normalized3}")
