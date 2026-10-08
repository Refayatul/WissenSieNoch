#!/usr/bin/env python3
import pathlib, re

claims_data = [
    # Housing (1-8)
    (1, 'housing', 'Apartments were allocated by the state.', 'de_Deutsche_Demokratische_Republik.txt', 'Die Wohnungen wurden vom Staat zugeteilt;'),
    (2, 'housing', 'There was no housing market in the GDR.', 'de_Deutsche_Demokratische_Republik.txt', 'Es gab in der DDR keinen Wohnungsmarkt.'),
    (3, 'housing', 'Prefabricated apartments offered comfort like running hot and cold water and central heating.', 'de_Plattenbau.txt', 'da sie Komfort wie fließend warmes und kaltes Wasser, Zentralheizung,'),
    (4, 'housing', 'Prefabricated apartments offered an indoor toilet and a bathtub.', 'de_Plattenbau.txt', 'Toilette in der Wohnung (Innen-WC) und Badewanne boten.'),
    (5, 'housing', 'The state housing construction program of 1972 aimed to eliminate the housing shortage.', 'de_Plattenbau.txt', 'führte zum staatlichen Wohnungsbauprogramm von 1972, das den Wohnraummangel'),
    (6, 'housing', 'The new prefabricated building type WBS 70 was created.', 'de_Plattenbau.txt', 'Zu diesem Zweck wurde der neue Plattenbautyp WBS 70 geschaffen,'),
    (7, 'housing', 'Apartment rents were regulated by the state at a low level in the GDR.', 'de_Plattenbau.txt', 'Wohnungsmieten wurden in der DDR staatlich auf ein niedriges Niveau reguliert,'),
    (8, 'housing', 'The provision of telephones remained very low.', 'de_Deutsche_Demokratische_Republik.txt', 'blieb die Versorgung mit Telefonen sehr gering ausgeprägt:'),

    # Work (9-16)
    (9, 'work', 'The basic unit of work organization was the collective, often in the form of the brigade.', 'de_Deutsche_Demokratische_Republik.txt', 'Basisgröße der Arbeitsorganisation war das Kollektiv, oft in Form der Brigade.'),
    (10, 'work', 'Job security was among the features of the GDR economic system.', 'de_Deutsche_Demokratische_Republik.txt', 'Zu den Merkmalen des DDR-Wirtschaftssystems zählten Arbeitsplatzsicherheit'),
    (11, 'work', 'There was a high employment rate of women compared to the social market economy of West Germany.', 'de_Deutsche_Demokratische_Republik.txt', 'und ein im Vergleich zur Sozialen Marktwirtschaft der alten Bundesrepublik hoher Beschäftigungsgrad von Frauen'),
    (12, 'work', 'The employment of women in the work process was encouraged through measures like reduced working hours.', 'de_Deutsche_Demokratische_Republik.txt', 'Die Mehrbeschäftigung von Frauen im Arbeitsprozess wurde durch Maßnahmen wie Arbeitszeitverkürzung'),
    (13, 'work', 'Women employment was encouraged through the extension of maternity leave.', 'de_Deutsche_Demokratische_Republik.txt', 'und Verlängerung des Mutterschaftsurlaubs sowie durch die starke Ausweitung'),
    (14, 'work', 'Enterprises included publicly owned enterprises, agricultural production cooperatives, and trade organizations.', 'de_Deutsche_Demokratische_Republik.txt', 'Volkseigene Betriebe (VEB), Landwirtschaftliche Produktionsgenossenschaften (LPG), Handelsorganisationen (HO)'),
    (15, 'work', 'It was guaranteed that every school leaver took up an apprenticeship.', 'de_Deutsche_Demokratische_Republik.txt', 'Es war garantiert, dass jeder Schulabgänger eine Lehre annahm'),
    (16, 'work', 'The Kombinate represented the most complex form of enterprise organization.', 'de_Deutsche_Demokratische_Republik.txt', 'Die komplexeste Form betrieblicher Organisation stellten die Kombinate dar.'),

    # Shopping (17-24)
    (17, 'shopping', 'Everyday goods were sold in retail shops, especially those of the cooperative Konsum organization and HO.', 'de_Deutsche_Demokratische_Republik.txt', 'In Einzelhandelsläden, vor allem denen der genossenschaftlichen Konsum-Organisation sowie der HO,'),
    (18, 'shopping', 'There were larger self-service stores called Kaufhallen.', 'de_Deutsche_Demokratische_Republik.txt', 'gab es größere Selbstbedienungsläden, die „Kaufhallen“ genannt wurden.'),
    (19, 'shopping', 'The supply of many products was subject to large fluctuations.', 'de_Deutsche_Demokratische_Republik.txt', 'Die Versorgung mit vielen Produkten unterlag großen Schwankungen.'),
    (20, 'shopping', 'Manufactured by a state monopoly, a Trabant took about ten years to acquire.', 'en_Trabant.txt', 'Manufactured by a state monopoly, a Trabant took about ten years to acquire.'),
    (21, 'shopping', 'East German buyers were placed on a waiting list of up to thirteen years.', 'en_Trabant.txt', 'East German buyers were placed on a waiting list of up to thirteen years.'),
    (22, 'shopping', 'The Trabant had body panels made of duroplast.', 'en_Trabant.txt', 'with the roof, boot lid, bonnet, wings and doors made of duroplast,'),
    (23, 'shopping', 'Intershop was a chain of retail stores operated in the German Democratic Republic.', 'en_Intershop.txt', 'Intershop was a chain of government-owned and operated retail stores in the German Democratic Republic'),
    (24, 'shopping', 'The East German mark was not accepted as payment in Intershops.', 'en_Intershop.txt', 'The East German mark was not accepted as payment.'),

    # Children and School (25-32)
    (25, 'children and school', 'The polytechnic secondary school was the general school form in the GDR school system and comprised ten classes.', 'de_Polytechnische_Oberschule.txt', 'war die allgemeine Schulform im Schulsystem der DDR und umfasste zehn Klassen.'),
    (26, 'children and school', 'There were uniform educational contents for all children up to class 8 and later class 10.', 'de_Deutsche_Demokratische_Republik.txt', 'einheitliche Bildungsinhalte für alle Kinder bis Klasse 8 (später 10)'),
    (27, 'children and school', 'Childcare was promoted through the strong expansion of childcare facilities such as crèche and kindergarten.', 'de_Deutsche_Demokratische_Republik.txt', 'durch die starke Ausweitung der Kinderbetreuungseinrichtungen (Kinderkrippe, Kindergarten) gefördert.'),
    (28, 'children and school', 'Membership in the Ernst Thälmann Pioneer Organisation was mostly closely interwoven with school.', 'de_Polytechnische_Oberschule.txt', 'Mit der Schule zumeist eng verwoben war die Mitgliedschaft in der Pionierorganisation Ernst Thälmann,'),
    (29, 'children and school', 'Young Pioneers had a blue neckerchief to wear for festive occasions.', 'de_Polytechnische_Oberschule.txt', 'deren äußeres Merkmal dann ein für festliche Anlässe zu tragendes blaues Halstuch war.'),
    (30, 'children and school', 'The Thälmann Pioneers had a red neckerchief as a distinguishing mark starting from 1973.', 'de_Polytechnische_Oberschule.txt', 'das der Thälmann-Pioniere, deren unterscheidbares Merkmal neben der Pionierkleidung ab 1973 ein rotes Halstuch war.'),
    (31, 'children and school', 'In the 8th grade, the majority of youths transitioned from the Thälmann Pioneers to the youth organization.', 'de_Polytechnische_Oberschule.txt', 'In der 8. Klasse erfolgte für die Mehrheit der Jugendlichen der Wechsel von den Thälmann-Pionieren'),
    (32, 'children and school', 'School provided targeted preparation for the future world of work through polytechnic education.', 'de_Deutsche_Demokratische_Republik.txt', 'die gezielte Vorbereitung auf die spätere Arbeitswelt durch polytechnische Ausbildung'),

    # Leisure (33-40)
    (33, 'leisure', 'The typical GDR Datsche consisted of a plot with a house built in lightweight construction.', 'de_Datsche.txt', 'Die typische DDR-Datsche bestand aus einem Grundstück mit einem in Leichtbauweise errichteten Haus,'),
    (34, 'leisure', 'The Datsche serves for leisure and recreation and enables hobby gardening.', 'de_Datsche.txt', 'das der Freizeit und der Erholung dient und Hobbygärtnerei ermöglicht.'),
    (35, 'leisure', 'Datschen could usually be reached from the main residence within an hour.', 'de_Datsche.txt', 'Die Datschen waren vom Hauptwohnsitz aus meist innerhalb einer Stunde zu erreichen.'),
    (36, 'leisure', 'It is estimated that there were about 3.4 million Datschen in the GDR.', 'de_Datsche.txt', 'Es wird geschätzt, dass es in der DDR etwa 3,4 Millionen Datschen gab'),
    (37, 'leisure', 'Most vacationers remained in the GDR, preferably at the Baltic Sea.', 'de_Deutsche_Demokratische_Republik.txt', 'Die meisten Urlauber blieben in der DDR, bevorzugt an der Ostsee,'),
    (38, 'leisure', 'Preferred holiday destinations were at the Baltic Sea, in the Thuringian Forest, and in the Elbe Sandstone Mountains.', 'de_Deutsche_Demokratische_Republik.txt', 'bevorzugt an der Ostsee, im Thüringer Wald und im Elbsandsteingebirge.'),
    (39, 'leisure', 'Unser Sandmännchen is a German children television programme produced since 1959.', 'de_Unser_Sandmännchen.txt', 'Unser Sandmännchen (kurz auch Sandmann) ist eine deutsche Kindersendung, die seit 1959 produziert wird'),
    (40, 'leisure', 'From 1959 to 1990, Unser Sandmännchen was broadcast on Deutscher Fernsehfunk in divided Germany.', 'de_Unser_Sandmännchen.txt', 'Von 1959 bis 1990 wurde im geteilten Deutschland sowohl Unser Sandmännchen beim Deutschen Fernsehfunk')
]

def verify_claims():
    files = {p.name: p.read_text(encoding='utf-8') for p in pathlib.Path('sources').glob('*.txt')}
    for cid, cat, claim, fn, q in claims_data:
        words = q.split()
        assert len(words) <= 15, f'Claim {cid} quote too long: {q}'
        assert q in files[fn] or ' '.join(q.split()) in ' '.join(files[fn].split()), f'Quote {cid} not in {fn}'
    print('All 40 claims verified perfectly against sources.')

if __name__ == '__main__':
    verify_claims()
