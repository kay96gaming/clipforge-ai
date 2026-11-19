BLACK, PURPLE_D, NEON, PINK = "#080510", "#160B2B", "#A020F0", "#FF36B8"
QSS = f"""
* {{ font-family: 'Segoe UI'; color: #EDE7F6; font-size: 13px; }}
QMainWindow, #root {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 {BLACK}, stop:1 {PURPLE_D}); }}
#sidebar {{ background: rgba(255,255,255,0.04); border-right: 1px solid rgba(160,32,240,0.35); }}
#logo {{ font-size: 20px; font-weight: 800; color: {PINK}; padding: 18px 14px; }}
QPushButton#nav {{ text-align: left; padding: 11px 18px; border: none; border-radius: 10px; margin: 2px 10px; background: transparent; }}
QPushButton#nav:hover {{ background: rgba(160,32,240,0.18); }}
QPushButton#nav:checked {{ background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 rgba(160,32,240,0.55), stop:1 rgba(255,54,184,0.35)); }}
QFrame#card, QGroupBox {{ background: rgba(255,255,255,0.055); border: 1px solid rgba(255,54,184,0.30); border-radius: 16px; }}
QGroupBox {{ margin-top: 14px; padding: 14px; }} QGroupBox::title {{ subcontrol-origin: margin; left: 14px; color: {PINK}; }}
QPushButton {{ padding: 9px 16px; border-radius: 10px; border: 1px solid rgba(160,32,240,0.6); background: rgba(160,32,240,0.18); }}
QPushButton:hover {{ background: rgba(160,32,240,0.38); }} QPushButton:disabled {{ color: #776b8a; border-color: #3a2c52; }}
QPushButton#primary {{ border: none; font-weight: 700; padding: 12px 22px;
  background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {NEON}, stop:1 {PINK}); }}
QLineEdit, QComboBox, QSpinBox, QTableWidget, QListWidget, QPlainTextEdit {{ background: rgba(8,5,16,0.7); border: 1px solid rgba(160,32,240,0.4); border-radius: 8px; padding: 6px; }}
QHeaderView::section {{ background: {PURPLE_D}; border: none; padding: 6px; color: {PINK}; }}
QProgressBar {{ border: 1px solid rgba(160,32,240,0.5); border-radius: 8px; text-align: center; background: rgba(8,5,16,0.7); height: 18px; }}
QProgressBar::chunk {{ border-radius: 8px; background: qlineargradient(x1:0,y1:0,x2:1,y2:0, stop:0 {NEON}, stop:1 {PINK}); }}
#title {{ font-size: 22px; font-weight: 700; }} #muted {{ color: #9c8fb8; }}
"""
