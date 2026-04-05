# Semantische Suche für lokale Medien

Diese Anwendung soll die inhaltliche Durchsuchung lokaler Bild und Videodateien per Text-Prompt oder Referenzbild ermöglichen. Durch lokale Modelle findet der gesamte Abgleich auf der eigenen GPU/CPU statt, wodurch die Daten privat bleiben und keine Cloud-Anbindung nötig ist.

Die kompilierte .exe ist auf GitHub unter **Releases** im Abschnitt **Erarbeitungs- und Reflexionsphase** zu finden. Es gibt zwei Varianten: eine ohne CUDA (CPU) und eine mit CUDA. Funktional sind beide identisch, jedoch kann die CUDA-Version die GPU nutzen und ist dadurch deutlich schneller. Da CUDA zu groß für GitHub ist, kann es nicht direkt in die kompilierte Datei integriert werden. Deshalb muss bei der CUDA-Version zuerst die mitgelieferte Setup-Datei für CUDA ausgeführt werden. Bei der Version ohne CUDA reicht es aus, das Archiv zu entpacken und die .exe zu starten.

Beim ersten Start muss das Programm mindestens ein Modell herunterladen und speichern. Dafür benötigt es Schreibrechte auf seinen eigenen Ordner. Falls diese nicht vorhanden sind, müssen sie gegeben werden, zum Beispiel indem die .exe als Administrator ausgeführt wird oder indem dem Ordner Schreibrechte gegeben werden. Wenn sich die Anwendung z. B. in „C:\Program Files\AISearchEngine“ befindet, kann dies über PowerShell (als Administrator) mit folgendem Befehl erfolgen:


```bash
icacls "C:\Program Files\AISearchEngine" /grant *S-1-5-32-545:(OI)(CI)M
```

# Eingabe

Unter **AI Prompt & Image** kann je nach Suchmodus der zu suchende Begriff eingegeben werden oder ein Bild ausgewählt werden. Aus diesem Bild wird automatisch ein AI-Prompt generiert, den man anschließend selbst noch bearbeiten kann.

Unter **Target Data** sind die zu durchsuchenden Dateien bzw. Ordner einzufügen.


# Suche

Unter **AI Settings** kann man unter **Comparison Logic** den Suchmodus einstellen. Entweder wird nach Keywords in den generierten AI-Prompts gesucht oder es werden die beiden Vektoren der Eingabe (Text oder Bild) und der zu durchsuchenden Dateien miteinander verglichen.

Aktuell kann in **KI-Modeel Version** zwischen zwei Modellen auswählen, die sich hauptsächlich in ihrer Größe unterscheiden.

Zusätzlich kann man die Generierung der Prompts über einige Parameter beeinflussen:

**Beam Size** bestimmt wie viele mögliche Textvarianten das Modell gleichzeitig berechnet und miteinander vergleicht.

**Min Length** legt fest wie lang der generierte Prompt mindestens sein muss, damit das Modell nicht zu kurze Beschreibungen erzeugt, zu lange lässt das Modell allerdings halluzinieren.

**Length Penalty** beeinflusst ob das Modell eher kürzere oder längere Beschreibungen generiert. Je nach Wert werden längere oder kürzere Texte bevorzugt.

**No Repeat** bestraft wenn Wortfolgen mehrfach hintereinander generiert werden und reduziert so Wiederholungen im Prompt.


Bei der ersten Suche für ein Modell wird dieses automatisch heruntergeladen, was etwas dauern kann. Die Modelle sollten anschließend im selben Verzeichnis wie die exe unter dem Ordner **AI_models** auffindbar sein.

Testbilder sind im **test** Ordner des Projekts vorhanden.

![UI](test/Readme.png)