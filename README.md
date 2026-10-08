# Wissen Sie noch – DDR Alltag Pipeline

Automatisierte YouTube-Produktionspipeline für den Kanal **„Wissen Sie noch“** zur Erstellung faktenbasierter, ruhiger historischer Dokumentationen über das Alltagsleben in der DDR.

## Video 1
**Titel**: *Alltag in der DDR: So lebten die Menschen in den 1970ern*  
**Dauer**: ca. 12 Minuten (1.733 Wörter Narration)  
**Ziel-Keyword**: `alltag in der ddr`  

### Kapitelstruktur
- `00:00` Einstieg: Was war „normal“?
- `01:05` Wohnen (Plattenbau WBS 70, Mieten, Zentralheizung, Telefonversorgung)
- `03:15` Arbeit (Betriebskollektive, Brigaden, Frauenberufstätigkeit, Arbeitsplatzsicherheit)
- `05:25` Einkaufen (Konsum, HO, Kaufhallen, Versorgungsdynamik, Trabant, Intershop)
- `07:35` Kinder und Schule (Kinderkrippen, Kindergärten, zehnklassige POS, Thälmann-Pioniere)
- `09:45` Freizeit (Datschenkultur, Urlaub an der Ostsee, Deutscher Fernsehfunk, Unser Sandmännchen)
- `11:35` Ausklang: Rückblick & Zuschauerfrage („Was haben Sie erlebt?“)

---

## Architektur & Pipeline

1. **Quellensammlung (`fetch_sources.py`)**:
   Zieht Volltextartikel von Wikipedia (Deutsch & Englisch) über die MediaWiki REST API und speichert diese nachweisbar in `sources/`.
2. **Faktenverifikation (`check_claims.py`)**:
   Prüft 40 Kernbehauptungen mit wörtlichen Quellenzitaten (max. 15 Wörter), um jegliche Halluzinationen oder unautorisierte Jahreszahlen/Eigennamen auszuschließen.
3. **Skript-Engine (`generate_final_script.py` / `script.txt`)**:
   Generiert die 1.733 Wörter lange deutsche Narration (formelle Anrede „Sie“, maximale Satzlänge 20 Wörter, neutraler Ton, frei von Propaganda).
4. **Sprachsynthese (`run_voice.sh`)**:
   Synthetisiert mit Piper TTS (`de_DE-thorsten-high.onnx`) und drosselt das Sprechtempo leicht (`ffmpeg -filter:a "atempo=0.93"`), um 12 Minuten 26 Sekunden glasklare Audionarration (`narration.wav`) zu erzeugen.
5. **Untertitelung (`captions.py`)**:
   Erzeugt zeitgenaue deutsche Untertitel (`captions.srt`) mittels `faster-whisper` (Small-Modell, int8 CPU).
6. **Bildrecherche & Attribution (`fetch_images.py` / `shots.txt`)**:
   Recherchiert 99 zeitgenössische Fotografien aus dem Bundesarchiv (CC BY-SA 3.0 Deutschland) via Wikimedia Commons Thumbnail CDN.
7. **Videoschnitt (`build_video.py`)**:
   Fügt Bildfolge, Audiospur und eingebrannte Untertitel zu `video.mp4` zusammen und exportiert `credits.txt`.
