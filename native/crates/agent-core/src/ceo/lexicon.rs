pub const STOPWORDS: &str = "
abbiamo aber about above adesso after again against agli alcuna alcune alcuni alcuno all
alla alle aller allez allo allons allora anche ancora and andare andata andate andato
andiamo any aquel aquela aquele aquella are ascolta auf aus aux avaient avais avait avec
avere avete aveva avevano avevo avez aviez avions avoir avons avra avrai avranno avremo
avrete avro avuta avute avuti avuto because been before beh bei being below bene between bin
bist bitte boh bonjour bonsoir both but can cannot car ceci cela ces cet cette che chez chi
circa coi col com come comme comment como con cosa cose cosi could cual cuales cuando cuanto
cui dagli dai dal dalla dalle dallo danke dans das decir degli dei dein deine del della
delle dello dem den denn der des detta detto deve devez devi devo devoir devono devons dice
dich dici diciamo dicono did die diese diesem diesen dieser dieses dimmi dir dire dite dizer
dobbiamo doch does doing dois doit doivent donc donde dont dopo dos dove dovere dovete down
dunque durch during each ein eine einem einen einer eines ela elas ele eles ella ellas elle
elles ello ellos entre era eran erano eras eres eri ero esa esas ese esos essa essas esse
essere esses essi esso est esta estais estamos estar estas este estes estos estou estoy euch
euer eure facciamo fai faire fais faisons fait faites fanno fare fate fatta fatte fatti
fatto faz fazeis fazem fazemos fazer fazes few finche foi font for forse fra from fue fui
further gegen gehabt gewesen gli gracias grazie habe haben haber hace hacemos hacen hacer
haces had hago hai hallo han hanno has hast hat hatte hatten have haver having hemos her
here hers herself him himself his hola how ich ihm ihn ihnen ihr ihre ils infatti into
invece ist its itself jede jeder jedes kann kannst kein keine keinem keinen keiner keines
laquelle las lei lequel les lesquelles lesquels leur leurs lhe lhes loro lorsque los lui mah
mai mais male mas meglio mein meine meno mentre merci mes meu meus mia mich mie miei minha
minhas mio mir mis mit molta molte molti molto mon more most mucha muchas mucho muchos muita
muitas muito muitos muss musst muy myself nach nas neanche negli nei nel nella nelle nello
nem nemmeno neppure nicht niente noi non nor nos nosotros nossa nossas nosso nossos nostra
nostre nostri nostro not notre nous nuestra nuestro nulla obrigada obrigado oder off ohne
okay once onde only ont oppure ora other otra otras otro otros ought our ours ourselves out
over ovvero own par para peggio pei pel pela pelas pelo pelos per perche percio pero peut
peuvent peux piu please poca pocas poche pochi poco pocos pode podeis podem podemos poder
podes poi por porque possiamo posso possono potere potete pouca poucas pouco poucos pour
pouvez pouvoir pouvons prego prima puede pueden puedes puedo puo puoi pure qua quais qual
qualche quale quali quand quando quanta quante quanti quanto quantos quasi que quel quell
quella quelle quelli quello quem quest questa queste questi questo qui quien quindi quoi
salut same sans sara sarai saranno saremo sarete saro scusa scusami sei sein seine sem
sempre senti ser ses seu seus she should siamo sido sie siete sin sind sino sob sobre sois
sollen some sommes somos son sondern sono sont sou sous soy spesso sta stai stanno stata
state stati stato stiamo sua suas subito such sue sugli sui suis sul sulla sulle sullo suo
suoi sur sus talvolta tanta tante tanti tanto tell tem temos tendes tenemos tener tengo
tenho tens ter tes teu teus than thank thanks that the their theirs them themselves then
there these they this those through tiene tienen tienes tinha tive toda todas todo todos ton
too tra tras tua tuas tudo tue tuo tuoi tus tutta tuttavia tutte tutti tutto uma umas una
unas und under une uno unos uns unser unsere unter until usted ustedes vai vais vamos van
vanno vas very veulent veut veux vogliamo voglio vogliono voi volere volete von vont vor vos
vosotros vostra vostre vostri vostro votre voulez vouloir voulons vous voy vuestra vuestro
vuoi vuole wann war waren warum was welche welchem welchen welcher welches wenn wer werden
were what when where which while who whom why wie will willst wir with wollen would you your
yours yourself yourselves zwischen
";

pub const GENERIC: &str = "
adesso aggiungere aggiungi apri aprimi aprire avvia avviare cerca cercare crea creami creare
create dammi devi dimmi fai fammi fare favore give grazie guarda lancia lanciare make
mettere metti mettimi mostra mostrami mostrare need nel nella nuova nuove nuovi nuovo open
ora please potresti puoi show start subito tell trova trovare usa usare vedere versione
voglio vorrei want
";

pub const GREETING: &str = r"^(ciao|buongiorno|buond[iì]|buonasera|buonanotte|salve|hey|ehi|hello|hi|good morning|good evening|good afternoon|hola|buenos d[ií]as|buenas tardes|buenas noches|bonjour|bonsoir|salut|hallo|guten morgen|guten tag|guten abend|ol[aá]|bom dia|boa tarde|boa noite)(\s+(nuxiva|assistente|amico|tutti|a tutti|assistant|friend))?([\s,!.?]+(come\s+va|come\s+stai|tutto\s+bene|come\s+butta|how\s+are\s+you|what's\s+up|how\s+is\s+it\s+going|c[oó]mo\s+est[aá]s|c[oó]mo\s+te\s+va|qu[eé]\s+tal|todo\s+bien|comment\s+[cç]a\s+va|comment\s+vas-tu|tout\s+va\s+bien|wie\s+geht\s+es\s+dir|wie\s+geht's|alles\s+gut|tudo\s+bem|como\s+vai))?[\s.?!]*$";

pub const SMALLTALK: &str = r"^(come\s+va|come\s+stai|tutto\s+bene|come\s+vanno\s+le\s+cose|how\s+are\s+you|how\s+is\s+it\s+going|what's\s+up|c[oó]mo\s+est[aá]s|c[oó]mo\s+te\s+va|qu[eé]\s+tal|todo\s+bien|comment\s+[cç]a\s+va|comment\s+vas-tu|tout\s+va\s+bien|wie\s+geht\s+es\s+dir|wie\s+geht's|alles\s+gut|tudo\s+bem|como\s+vai)(\s+(oggi|ora|adesso|today|now|hoy|ahora|aujourd'hui|maintenant|heute|jetzt|hoje|agora))?[\s.?!]*$";

pub const IDENTITY: &str = r"^(chi\s+sei|come\s+ti\s+chiami|qual\s+[eè]\s+il\s+tuo\s+nome|qual\s+[eè]\s+la\s+tua\s+funzione|presentati|raccontami\s+di\s+te|cosa\s+sai\s+fare|cosa\s+puoi\s+fare|cosa\s+fai|who\s+are\s+you|what\s+is\s+your\s+name|what\s+can\s+you\s+do|introduce\s+yourself|qui[eé]n\s+eres|c[oó]mo\s+te\s+llamas|qu[eé]\s+puedes\s+hacer|qu[eé]\s+sabes\s+hacer|pres[eé]ntate|qui\s+es-tu|comment\s+t'appelles-tu|que\s+peux-tu\s+faire|pr[eé]sente-toi|wer\s+bist\s+du|wie\s+hei[sß]t\s+du|was\s+kannst\s+du\s+tun|stelle\s+dich\s+vor|quem\s+[eé]\s+voc[eê]|como\s+voc[eê]\s+se\s+chama|o\s+que\s+voc[eê]\s+pode\s+fazer|apresente-se)[\s.?!]*$";
