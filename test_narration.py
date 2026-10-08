#!/usr/bin/env python3
import re

# Comprehensive list of allowed proper names and numbers from the 40 verified claims:
# Names: DDR, Deutsche Demokratische Republik, WBS 70, Bundesrepublik, VEB, LPG, HO, Kombinate,
#        Konsum, Kaufhallen, Trabant, Duroplast, Intershop, Forumchecks, POS, Polytechnische Oberschule,
#        Ernst Thälmann, Jungpioniere, Thälmann-Pioniere, FDJ, Datsche, Ostsee, Thüringer Wald,
#        Elbsandsteingebirge, Unser Sandmännchen, Sandmann, Deutscher Fernsehfunk
# Numbers/Dates: 1972, 70 (in WBS 70), 10 (zehn), 13 (dreizehn), 8 (acht), 1973, 1 (eine/ein),
#                3,4 Millionen (3.4), 1959, 1990

hook = """
Wie sah das alltägliche Leben in der DDR wirklich aus?
Viele Menschen verbinden damit ganz bestimmte Bilder und prägende Erinnerungen.
Der Alltag war durch feste Gewohnheiten und klare staatliche Rahmenbedingungen geregelt.
Von morgens bis abends folgten die Menschen festen Abläufen in Familie, Schule und Beruf.
Wohnungen wurden vom Staat zugeteilt und die monatlichen Mieten blieben sehr niedrig.
In den Betrieben arbeiteten die Menschen eng zusammen in Kollektiven und Brigaden.
Kinder besuchten Krippen, Kindergärten und die zehnklassige Polytechnische Oberschule.
Für den Einkauf des täglichen Bedarfs gab es Läden von Konsum und HO.
Bei langlebigen Konsumgütern wie dem Trabant mussten die Käufer jedoch viel Geduld mitbringen.
Nach der Schicht bot die eigene Datsche im Grünen einen beliebten Ort der Ruhe.
Im Urlaub reisten Familien an die Ostsee oder wanderten im Thüringer Wald.
Am Abend sahen Kinder und Eltern das Sandmännchen im Deutschen Fernsehfunk.
Wir laden Sie ein zu einer ruhigen und sachlichen Betrachtung dieses Alltags.
Begleiten Sie uns durch Wohnen, Arbeit, Einkauf, Schule und Freizeit dieser Epoche.
"""

ch1_wohnen = """
In der DDR existierte kein freier Wohnungsmarkt.
Wohnungen wurden den Bürgern direkt durch den Staat zugeteilt.
Wer eine Wohnung benötigte, stellte einen formellen Antrag bei der zuständigen Wohnungsbehörde.
Die Wohnungszuteilung erfolgte nach vorgegebenen Richtlinien und Kriterien der staatlichen Stellen.
Besonders für alleinstehende Erwachsene ohne Kinder war es oft schwierig, eine Wohnung zu erhalten.
Die Wohnungsmieten wurden in der DDR staatlich auf ein niedriges Niveau reguliert.
Niedrige Mieten sorgten dafür, dass die Wohnkosten für alle Bürger bezahlbar blieben.
Im Jahr 1972 beschloss die Führung das umfassende staatliche Wohnungsbauprogramm.
Dieses Programm hatte das Ziel, den Wohnraummangel im Land bis 1990 vollständig zu beseitigen.
Zu diesem Zweck wurde der moderne Plattenbautyp WBS 70 entwickelt.
Große Neubaugebiete und ganze Stadtteile entstanden aus diesen vorgefertigten Betonplatten.
Viele Familien freuten sich sehr über den Einzug in eine solche Neubauwohnung.
Die Plattenbauwohnungen boten den Bewohnern einen für damalige Verhältnisse beachtlichen Wohnkomfort.
Dazu gehörte vor allem fließend warmes und kaltes Wasser direkt aus der Leitung.
Zudem waren die modernen Wohnungen mit einer zuverlässigen Zentralheizung ausgestattet.
Das mühsame Tragen von schweren Kohlen für alte Öfen entfiel im Plattenbau vollständig.
Auch eine eigene Toilette in der Wohnung und eine feste Badewanne waren vorhanden.
Ein eigenes Badezimmer mit Innen-WC galt vielen Menschen als spürbarer Gewinn an Lebensqualität.
Allerdings blieb die Versorgung mit Telefonen im Alltag sehr gering ausgeprägt.
Nur ein kleiner Teil der Bevölkerung besaß einen eigenen Telefonanschluss in den eigenen vier Wänden.
Wer dringend telefonieren musste, nutzte meist öffentliche Fernsprecher auf der Straße oder bei der Post.
Auf einen privaten Telefonanschluss warteten die Menschen oft viele Jahre lang.
Das Wohnen im Plattenbau brachte modernen Komfort mit festen niedrigen Mieten, während Telefone selten blieben.
"""

ch2_arbeit = """
Die Arbeit bildete für die Erwachsenen den festen Mittelpunkt des täglichen Ablaufs.
Das Wirtschaftssystem der DDR zeichnete sich durch eine hohe Arbeitsplatzsicherheit aus.
Fast alle Betriebe befanden sich im staatlichen Besitz oder waren als Genossenschaften organisiert.
Zu den wichtigsten Betriebsformen gehörten Volkseigene Betriebe, Handelsorganisationen und Landwirtschaftliche Produktionsgenossenschaften.
Die größte und komplexeste Form der betrieblichen Organisation bildeten die Kombinate.
In einem Kombinat wurden zahlreiche Produktionsstätten und Zulieferer eines ganzen Industriezweigs zusammengefasst.
Die Basisgröße der alltäglichen Arbeitsorganisation in den Betrieben war das Kollektiv.
Sehr häufig war dieses Arbeitskollektiv in Form einer Brigade organisiert.
In der Brigade meisterten die Kollegen nicht nur gemeinsam ihre täglichen Arbeitsaufgaben.
Die Mitglieder einer Brigade trafen sich oft auch nach Feierabend zu gemeinsamen Freizeitaktivitäten.
Ein weiteres prägendes Merkmal war der hohe Beschäftigungsgrad von Frauen.
Im Vergleich zur Bundesrepublik arbeiteten in der DDR deutlich mehr Frauen in festen Berufen.
Der Staat förderte die Mehrbeschäftigung von Frauen im Arbeitsprozess mit gezielten Maßnahmen.
Dazu gehörte unter anderem eine Verkürzung der täglichen oder wöchentlichen Arbeitszeit für Mütter.
Ebenso wurde der bezahlte Mutterschaftsurlaub für Mütter spürbar verlängert.
Frauen erhielten dadurch mehr Raum, Berufstätigkeit und Kindererziehung miteinander zu verbinden.
Für junge Menschen war der Übergang von der Schule in den Beruf lückenlos organisiert.
Es war gesetzlich garantiert, dass jeder Schulabgänger eine feste Lehre in einem Betrieb antreten konnte.
Niemand musste fürchten, nach der Schulzeit ohne Ausbildungsplatz oder feste Beschäftigung dazustehen.
Die Arbeitswelt bot sichere Arbeitsplätze und gemeinsame Brigaden, während Frauen durch besondere Maßnahmen im Beruf unterstützt wurden.
"""

ch3_einkaufen = """
Der tägliche Einkauf erforderte von den Bürgern Überblick und praktische Erfahrung.
Waren des täglichen Bedarfs wurden vor allem über zwei große Handelsketten verkauft.
Dazu zählten die genossenschaftliche Konsum-Organisation und die staatliche Handelsorganisation HO.
Neben vielen kleineren Verkaufsstellen in den Wohngebieten gab es größere Selbstbedienungsläden.
Diese modernen Geschäfte mit Selbstbedienung wurden im alltäglichen Sprachgebrauch als Kaufhallen bezeichnet.
Hier kauften die Menschen frisches Brot, Milchprodukte, Grundnahrungsmittel und Waren für den Haushalt.
Die Versorgung mit vielen Produkten unterlag jedoch im Alltag spürbaren Schwankungen.
Einige Waren des Grundbedarfs waren günstig und stets vorhanden, während andere Güter zeitweise fehlten.
Wer ein eigenes Auto anschaffen wollte, benötigte sehr viel Geduld.
Die Herstellung des beliebten Kleinwagens Trabant lag in den Händen eines staatlichen Monopols.
Ein neuer Trabant brauchte rund zehn Jahre, bis er nach der Bestellung ausgeliefert wurde.
Die Käufer wurden auf Listen geführt und warteten oft bis zu dreizehn Jahre auf ihr Fahrzeug.
Die Karosserieteile des Trabant wurden aus dem speziellen Werkstoff Duroplast hergestellt.
Duroplast erwies sich als widerstandsfähig gegen Rost und überzeugte durch eine lange Lebensdauer.
Für besondere Konsumwünsche gab es die staatliche Kette Intershop.
Intershop betrieb eigene Einzelhandelsgeschäfte im gesamten Land.
In diesen Geschäften wurden hochwertige Importwaren und Konsumgüter aus westlichen Ländern verkauft.
Die reguläre Mark der DDR wurde im Intershop jedoch nicht als Zahlungsmittel angenommen.
Dort durfte man ausschließlich mit konvertierbaren Währungen und später mit speziellen Forumchecks bezahlen.
Der Einkauf war geprägt von Konsum, HO und Kaufhallen, während langlebige Güter wie der Trabant lange Wartezeiten erforderten.
"""

ch4_kinder = """
Für Kinder und Jugendliche bot die DDR ein engmaschiges und einheitliches System.
Die Betreuung begann für viele Kinder schon früh in der Kinderkrippe.
Der Staat trieb den Ausbau von Kinderbetreuungseinrichtungen wie Kinderkrippen und Kindergärten stark voran.
Diese Einrichtungen ermöglichten es Eltern, ihrer Arbeit nachzugehen und die Familie gut zu versorgen.
Nach der Zeit im Kindergarten wurden die Kinder gemeinsam eingeschult.
Die allgemeine Schulform im gesamten Schulsystem war die Polytechnische Oberschule, kurz POS.
Die Polytechnische Oberschule umfasste genau zehn Klassen für alle Schülerinnen und Schüler.
Bis zur Klasse 8 und später bis zur Klasse 10 galten einheitliche Bildungsinhalte für alle Kinder.
Eine Trennung nach unterschiedlichen Schultypen gab es in diesen zehn Klassen nicht.
Ein fester Bestandteil des Unterrichts war die gezielte Vorbereitung auf die spätere Arbeitswelt.
Dies geschah durch eine regelmäßige polytechnische Ausbildung mit praktischen Unterrichtstagen im Betrieb.
Eng mit dem Schulleben verknüpft war die Mitgliedschaft in der Pionierorganisation Ernst Thälmann.
In der ersten Klasse wurden die Kinder feierlich in die Reihen der Jungpioniere aufgenommen.
Als äußeres Kennzeichen trugen die Jungpioniere zu besonderen Feiertagen ein blaues Halstuch.
Ab der vierten Klasse traten die Schüler dann den Thälmann-Pionieren bei.
Ab dem Jahr 1973 trugen die Thälmann-Pioniere ein rotes Halstuch als erkennbares Merkmal.
In der Klasse 8 wechselten die allermeisten Jugendlichen schließlich zur Jugendorganisation FDJ.
Die zehnklassige Polytechnische Oberschule und ausgebaute Kinderbetreuung prägten das Aufwachsen gemeinsam mit der Pionierorganisation Ernst Thälmann.
"""

ch5_freizeit = """
Nach der Arbeit und an freien Wochenenden suchten viele Menschen Ruhe in der Natur.
Ein besonders beliebter und weit verbreiteter Rückzugsort war die eigene Datsche.
Es wird geschätzt, dass es in der DDR rund 3,4 Millionen solcher Datschen gab.
Die typische Datsche bestand aus einem Grundstück mit einem in Leichtbauweise errichteten Haus.
Sie diente vor allem der persönlichen Erholung und Freizeit und ermöglichte praktische Hobbygärtnerei.
Dort bauten die Familien mit Vorliebe eigenes Obst und Gemüse an und genossen die Stille.
Die meisten Datschen lagen so nah, dass man sie vom Hauptwohnsitz innerhalb einer Stunde erreichen konnte.
Auch im Sommerurlaub verbrachten die meisten Bürger ihre Ferien innerhalb der Landesgrenzen.
Sehr viele Urlauber reisten an die sonnigen Strände der Ostsee.
Ebenso geschätzte Reiseziele im Inland waren der Thüringer Wald und das Elbsandsteingebirge.
Am Abend gehörte das gemeinsame Fernsehen zum festen Ritual vieler Familien.
Bereits seit dem Jahr 1959 produzierte das Land die beliebte Kindersendung Unser Sandmännchen.
Von 1959 bis 1990 begleitete die Sendung im Deutschen Fernsehfunk die Kinder jeden Abend.
Mit einer kurzen Geschichte und einer Prise Traumsand schloss der Sandmann den Tag friedlich ab.
Die freie Zeit gehörte der Erholung im Garten auf der Datsche, dem Urlaub an der Ostsee und dem Sandmännchen.
"""

closing = """
So gestaltete sich das alltägliche Leben in der DDR zwischen Beruf, Schule und Freizeit.
Feste Strukturen, bezahlbare Wohnungen und verlässliche Arbeitsplätze gaben den Menschen einen festen Rahmen.
Gleichzeitig erforderten knappe Telefone, schwankende Angebote und lange Wartezeiten auf Autos Geduld und Organisationstalent.
Die Erinnerungen an diese Epoche sind bei den Menschen bis heute sehr vielfältig.
Manche denken mit Freude an den Zusammenhalt in der Brigade oder die Sommer auf der Datsche.
Andere erinnern sich vor allem an die spürbaren Begrenzungen und Engpässe im Alltag.
Geschichte wird besonders lebendig, wenn Zeitzeugen von ihren ganz persönlichen Erlebnissen berichten.
Was haben Sie damals in der DDR erlebt?
Welche Erinnerungen haben Sie an das Wohnen, die Arbeit, die Schule oder Ihre Freizeit?
Hinterlassen Sie Ihre persönlichen Gedanken und Erfahrungen gern unten in den Kommentaren.
"""

full_text = "\n".join([hook, ch1_wohnen, ch2_arbeit, ch3_einkaufen, ch4_kinder, ch5_freizeit, closing])
sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', full_text) if s.strip()]
print(f"Total sentences: {len(sentences)}")
words = sum(len(s.split()) for s in sentences)
print(f"Total words: {words}")

long_sentences = [(i, len(s.split()), s) for i, s in enumerate(sentences, 1) if len(s.split()) > 20]
if long_sentences:
    print(f"FAILED: {len(long_sentences)} sentences > 20 words:")
    for num, wlen, s in long_sentences:
        print(f"  #{num} ({wlen} words): {s}")
else:
    print("SUCCESS: All sentences <= 20 words!")

# Check that plain text has no markdown headers, brackets, stage directions
for s in sentences:
    assert not s.startswith('#'), f"Header found: {s}"
    assert '[' not in s and ']' not in s, f"Bracket found: {s}"
    assert '(' not in s and ')' not in s, f"Parenthesis found: {s}"
print("SUCCESS: Clean plain text format.")
