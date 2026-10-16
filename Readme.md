# Aktiendepot & Portfolio-Verwaltung

Eine moderne, webbasierte Flask-Anwendung zur Verwaltung eines persönlichen Aktiendepots. Die Anwendung holt Live- und historische Marktdaten über die Yahoo Finance API (`yahooquery`) ein, visualisiert den Depotverlauf sowie Einzelwerte mit Chart.js und bietet eine übersichtliche Detailansicht inklusive umfassender Kennzahlen (KGV, Beta, Dividendenrendite, Ex-Div-Datum, 52W-Hoch/Tief, All-Time High/Low) mit erklärenden Tooltips.

## 🚀 Features

* **Depot-Übersicht:** Gesamtwert in EUR, Gewinn/Verlust-Berechnung (unterstützt EUR- und USD-Assets mit automatischer Währungsumrechnung).
* **Asset-Detailansicht (Modals):** 
  * Umfassende Yahoo-Finanzkennzahlen (KGV, Beta, Dividenden, Ex-Div-Datum, 52-Wochen-Spanne, ATH/ATL) mit Hover-Erklärungen.
  * Asynchron per Fetch nachgeladener 1-Jahres-Kursverlaufs-Chart mit optimierter Achsendarstellung.
* **Transaktions- & Dividendenmanagement:** Käufe erfassen, bearbeiten oder löschen sowie erfasste Dividenden verwalten.
* **Aktiensuche:** Integrierte Yahoo-Suche zum schnellen Finden und Anlegen von Aktien und ETFs.
* **Charts:** Interaktive Diagramme (Asset-Allocation nach Währungen, historischer Depotverlauf, Einzelkurs-Charts) via Chart.js.
* **Sicherheit & Benutzerverwaltung:** Authentifizierung via Flask-Login mit Passwort-Hashing und integriertem Admin-Skript zur Benutzererstellung.

---

## 🛠️ Technische Architektur

* **Backend:** Python 3.12+, Flask, Flask-SQLAlchemy, Flask-Login, `yahooquery`
* **Frontend:** Bootstrap 5, Chart.js
* **Datenbank:** SQLite (`portfolio.db`)
* **Production Stack:** Gunicorn (WSGI-Server) hinter einem Apache Reverse Proxy (mit SSL) unter Linux / Oracle Linux.

---

## 📦 Installation & Einrichtung (Linux / Produktionsserver)

Diese Anleitung beschreibt die Einrichtung auf einem Linux-Server mit systemd und Gunicorn.
Die Pfade musst du bitte anpassen. Da ist immer dann notwendig wenn `hergen` auftaucht.
Das ist mein Vorname; ja ich weiss, kennt keine Sau.

### 1. Repository klonen & Verzeichnis vorbereiten
```bash
git clone https://github.com/hergla/Aktien.git ~/Aktien
cd ~/Aktien
```

### 2. Python Virtual Environment (`venv`) einrichten
Erstelle ein virtuelles Environment und installiere die benötigten Abhängigkeiten:
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 3. Gunicorn-Konfiguration erstellen
Erstelle im Projektverzeichnis (`~/Aktien`) eine Konfigurationsdatei namens `gunicorn.conf.py`:

```python
workers = 3
bind = "127.0.0.1:5002"
accesslog = "/home/hergen/Aktien/log/access.log"
errorlog = "/home/hergen/Aktien/log/error.log"
accesslogformat = '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s"'
loglevel = "info"
```
*(Hinweis: Erstelle vorher den Log-Ordner mit `mkdir -p ~/Aktien/log`)*

---

## 👤 Benutzerverwaltung (`user_admin.py`)

Da die Registrierung in der Anwendung geschützt ist, werden Benutzer über ein separates Administrationsskript in der Datenbank angelegt.

Führe das Skript im aktivierten Virtual Environment aus, um einen Benutzer hinzuzufügen:
```bash
source venv/bin/activate
python user_admin.py
```
*(Folge den Anweisungen im Terminal, um Benutzernamen und Passwort einzugeben).*

---

## 🧪 Manueller Start & Test mit Gunicorn

Bevor du den systemd-Dienst einrichtest, kannst du Gunicorn manuell im Vordergrund starten, um zu prüfen, ob die Anwendung fehlerfrei startet und reagiert:

```bash
source venv/bin/activate
gunicorn -c gunicorn.conf.py app:app
```
Du solltest die Gunicorn-Logausgabe in den Logfiles sehen und die App lokal (bzw. über den Proxy) testen können. Zum Beenden drücke `Strg + C`.

---

## ⚙️ systemd Service einrichten

Damit die Anwendung als Hintergrunddienst stabil läuft und beim Systemstart automatisch mitgestartet wird, richte einen systemd-Service ein.

1. Erstelle die Service-Datei mit Root-Rechten:
   ```bash
   sudo nano /etc/systemd/system/hlaktien.service
   ```

2. Füge folgenden Inhalt ein (Pfade, Benutzer und Umgebungsvariablen ggf. anpassen):
   ```ini
   [Unit]
   Description=Gunicorn instance to serve Flask Aktiendepot
   After=network.target

   [Service]
   User=hergen
   Group=hergen
   WorkingDirectory=/home/hergen/Aktien
   Environment="PATH=/home/hergen/Aktien/venv/bin"
   Environment="SECRET_KEY=dein-geheimer-schluessel-hier"
   ExecStart=/home/hergen/Aktien/venv/bin/gunicorn -c gunicorn.conf.py app:app

   [Install]
   WantedBy=multi-user.target
   ```

3. systemd neu laden und den Dienst aktivieren sowie starten:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl start hlaktien.service
   sudo systemctl enable hlaktien.service
   ```

4. Status des Dienstes prüfen:
   ```bash
   sudo systemctl status hlaktien.service
   ```

---

## 🌐 Apache Reverse Proxy & SSL Konfiguration

Um die App sicher per HTTPS (Port 443) über Apache erreichbar zu machen, lege eine VirtualHost-Konfiguration an (z. B. unter `/etc/httpd/conf.d/aktien-ssl.conf`):

```apache
<VirtualHost *:443>
    ServerName deine-domain.de

    SSLEngine on
    SSLCertificateFile /pfad/zu/fullchain.pem
    SSLCertificateKeyFile /pfad/zu/privkey.pem

    ProxyPreserveHost On
    ProxyPass /aktien/ http://10.1.1.100:5002/
    ProxyPassReverse /aktien/ http://10.1.1.100:5002/
    ProxyPass /aktien http://10.1.1.100:5002/
    ProxyPassReverse /aktien http://10.1.1.100:5002/

    RequestHeader set X-Forwarded-Proto "https"
    RequestHeader set X-Forwarded-Prefix "/aktien"
</VirtualHost>
```

Teste die Konfiguration und starte den Apache-Webserver neu:
```bash
sudo apachectl configtest
sudo systemctl restart httpd
```

---

## 📝 Lizenz
Dieses Projekt ist für den privaten Gebrauch bestimmt.