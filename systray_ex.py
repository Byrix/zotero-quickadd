import sys
from PyQt5.QtWidgets import QApplication, QSystemTrayIcon, QMenu, QAction, QWidget, QVBoxLayout, QLineEdit
from PyQt5.QtGui import QIcon
from PyQt5.QtCore import Qt, QTimer
import crossref_commons.retrieval
import re
from pyzotero import zotero
import datetime
import requests
from nameparser import HumanName
import os
from dotenv import load_dotenv

load_dotenv()
LIBRARY_ID = os.getenv('LIBRARY_KEY')
API_KEY = os.getenv('API_KEY')


class TextInputDialog(QWidget):
    def __init__(self, icon, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Text Input")
        self.notification_timer = QTimer()
        self.zot = zotero.Zotero(LIBRARY_ID, 'user', API_KEY)

        layout = QVBoxLayout()
        self.input_text = QLineEdit()
        layout.addWidget(self.input_text)

        self.icon = icon

        self.setLayout(layout)

        self.input_text.returnPressed.connect(self.process_input)

    def process_input(self):
        text = self.input_text.text()
        if text=='': return
        self.input_text.clear()
        self.hide()

        entry = None
        if re.search('[0-9]{10}', text):
            # 9780415263405
            meta = requests.get(f"https://openlibrary.org/api/books?bibkeys=ISBN:{text}&jscmd=data&format=json").json()[f"ISBN:{text}"]
            entry = self.zot.item_template('book', None)
            print(entry)
            print(meta)

            entry['title'] = f"{meta['title']}: {meta['subtitle']}"
            # entry['numPages'] = meta['number_of_pages']
            entry['ISBN'] = text
            entry['url'] = meta['url']
            entry['shortTitle'] = meta['title']
            entry['date'] = meta['publish_date']
            entry['publisher'] = meta['publishers'][0]['name']
            entry['place'] = meta['publish_places'][0]['name']

            creators = []
            for author in meta['authors']:
                name = HumanName(author['name'])
                creators.append({'creatorType': 'author', 'firstName': name.first, 'lastName': name.last})
            entry['creators'] = creators

        elif re.search('[0-9]+\.[0-9]+\/', text):
            meta = crossref_commons.retrieval.get_publication_as_json(text)
            entry = self.zot.item_template('journalArticle', None)

            entry['title'] = meta['title'][0]
            entry['publicationTitle'] = meta['container-title'][0]
            entry['volume'] = meta['volume']
            entry['pages'] = meta['page']
            entry['date'] = meta['published']['date-parts'][0][0]
            entry['DOI'] = meta['DOI']
            entry['ISSN'] = meta['ISSN'][0]
            entry['url'] = meta['resource']['primary']['URL']

            entry['creators'] = [{'creatorType': 'author', 'firstName': author['given'], 'lastName': author['family']} for author in
                                 meta['author']]
        else:
            self.send_msg("Type not recognised", 'w')

        if entry is not None:
            entry['accessDate'] = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            resp = self.zot.create_items([entry])
            if len(resp['success']) > 0:
                self.send_msg(f"Successfully added {entry['title']}")
            else:
                self.send_msg(f"Failed to add {entry['title']}", 'w')
            # print(resp)

    def send_msg(self, text, level='i'):
        if level == 'w':
            level = QSystemTrayIcon.Warning
        elif level == 'c':
            level = QSystemTrayIcon.Critical
        else:
            level = QSystemTrayIcon.Information

        self.icon.showMessage('Citation Quickadd', text, level)
        self.notification_timer.start(1000)


def main():
    # Create a PyQt application instances
    app = QApplication(sys.argv)
    tray_icon = QSystemTrayIcon()
    text_input_action = QAction("Enter Text")
    text_input_dialog = TextInputDialog(icon=tray_icon)

    # Set data
    tray_icon.activated.connect(lambda reason: text_input_dialog.show() if reason == QSystemTrayIcon.Trigger else None)
    tray_icon.setIcon(QIcon('./quote-grey.png'))

    tray_icon.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

# Icon
# <a href="https://www.flaticon.com/free-icons/quote" title="quote icons">Quote icons created by heisenberg_jr - Flaticon</a>
