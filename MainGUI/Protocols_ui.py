# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'Protocols.ui'
##
## Created by: Qt User Interface Compiler version 6.9.0
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QComboBox, QGridLayout,
    QLabel, QLineEdit, QListWidget, QListWidgetItem,
    QPushButton, QSizePolicy, QWidget)

class Ui_protocols(object):
    def setupUi(self, protocols):
        if not protocols.objectName():
            protocols.setObjectName(u"protocols")
        protocols.resize(1261, 601)
        self.label = QLabel(protocols)
        self.label.setObjectName(u"label")
        self.label.setGeometry(QRect(10, 10, 131, 31))
        font = QFont()
        font.setPointSize(12)
        self.label.setFont(font)
        self.label_2 = QLabel(protocols)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setGeometry(QRect(40, 50, 91, 16))
        self.num_cells = QLabel(protocols)
        self.num_cells.setObjectName(u"num_cells")
        self.num_cells.setGeometry(QRect(140, 80, 49, 21))
        font1 = QFont()
        font1.setPointSize(14)
        self.num_cells.setFont(font1)
        self.listWidget = QListWidget(protocols)
        self.listWidget.setObjectName(u"listWidget")
        self.listWidget.setGeometry(QRect(30, 270, 901, 261))
        self.label_4 = QLabel(protocols)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setGeometry(QRect(330, 240, 101, 16))
        self.addStage = QPushButton(protocols)
        self.addStage.setObjectName(u"addStage")
        self.addStage.setGeometry(QRect(820, 200, 75, 24))
        self.ncells = QLabel(protocols)
        self.ncells.setObjectName(u"ncells")
        self.ncells.setGeometry(QRect(150, 50, 49, 16))
        self.layoutWidget = QWidget(protocols)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.layoutWidget.setGeometry(QRect(30, 83, 909, 101))
        self.gridLayout = QGridLayout(self.layoutWidget)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setContentsMargins(0, 0, 0, 0)
        self.label_5 = QLabel(self.layoutWidget)
        self.label_5.setObjectName(u"label_5")

        self.gridLayout.addWidget(self.label_5, 0, 11, 1, 1)

        self.label_6 = QLabel(self.layoutWidget)
        self.label_6.setObjectName(u"label_6")

        self.gridLayout.addWidget(self.label_6, 0, 6, 1, 1)

        self.label_13 = QLabel(self.layoutWidget)
        self.label_13.setObjectName(u"label_13")

        self.gridLayout.addWidget(self.label_13, 0, 3, 1, 1)

        self.label_10 = QLabel(self.layoutWidget)
        self.label_10.setObjectName(u"label_10")

        self.gridLayout.addWidget(self.label_10, 0, 5, 1, 1)

        self.stim_time = QLineEdit(self.layoutWidget)
        self.stim_time.setObjectName(u"stim_time")

        self.gridLayout.addWidget(self.stim_time, 2, 10, 1, 1)

        self.groupsNumbers = QLabel(self.layoutWidget)
        self.groupsNumbers.setObjectName(u"groupsNumbers")

        self.gridLayout.addWidget(self.groupsNumbers, 0, 9, 1, 1)

        self.groups_period = QLineEdit(self.layoutWidget)
        self.groups_period.setObjectName(u"groups_period")

        self.gridLayout.addWidget(self.groups_period, 2, 6, 1, 1)

        self.stim_type = QComboBox(self.layoutWidget)
        self.stim_type.addItem("")
        self.stim_type.addItem("")
        self.stim_type.addItem("")
        self.stim_type.addItem("")
        self.stim_type.addItem("")
        self.stim_type.addItem("")
        self.stim_type.setObjectName(u"stim_type")
        self.stim_type.setFrame(True)

        self.gridLayout.addWidget(self.stim_type, 2, 1, 1, 1)

        self.jitter = QCheckBox(self.layoutWidget)
        self.jitter.setObjectName(u"jitter")

        self.gridLayout.addWidget(self.jitter, 2, 5, 1, 1)

        self.label_11 = QLabel(self.layoutWidget)
        self.label_11.setObjectName(u"label_11")

        self.gridLayout.addWidget(self.label_11, 0, 4, 1, 1)

        self.label_15 = QLabel(self.layoutWidget)
        self.label_15.setObjectName(u"label_15")

        self.gridLayout.addWidget(self.label_15, 0, 2, 1, 1)

        self.repeats = QLineEdit(self.layoutWidget)
        self.repeats.setObjectName(u"repeats")

        self.gridLayout.addWidget(self.repeats, 2, 11, 1, 1)

        self.label_3 = QLabel(self.layoutWidget)
        self.label_3.setObjectName(u"label_3")

        self.gridLayout.addWidget(self.label_3, 2, 0, 1, 1)

        self.on_time = QLineEdit(self.layoutWidget)
        self.on_time.setObjectName(u"on_time")

        self.gridLayout.addWidget(self.on_time, 2, 3, 1, 1)

        self.groups_number = QLineEdit(self.layoutWidget)
        self.groups_number.setObjectName(u"groups_number")

        self.gridLayout.addWidget(self.groups_number, 2, 9, 1, 1)

        self.prob_stim = QCheckBox(self.layoutWidget)
        self.prob_stim.setObjectName(u"prob_stim")

        self.gridLayout.addWidget(self.prob_stim, 2, 2, 1, 1)

        self.background_freq = QLineEdit(self.layoutWidget)
        self.background_freq.setObjectName(u"background_freq")

        self.gridLayout.addWidget(self.background_freq, 2, 4, 1, 1)

        self.group_size = QLineEdit(self.layoutWidget)
        self.group_size.setObjectName(u"group_size")

        self.gridLayout.addWidget(self.group_size, 2, 8, 1, 1)

        self.label_8 = QLabel(self.layoutWidget)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setTextFormat(Qt.TextFormat.PlainText)

        self.gridLayout.addWidget(self.label_8, 0, 10, 1, 1)

        self.label_14 = QLabel(self.layoutWidget)
        self.label_14.setObjectName(u"label_14")

        self.gridLayout.addWidget(self.label_14, 0, 7, 1, 1)

        self.is_manual_sequence = QCheckBox(self.layoutWidget)
        self.is_manual_sequence.setObjectName(u"is_manual_sequence")

        self.gridLayout.addWidget(self.is_manual_sequence, 2, 7, 1, 1)

        self.label_9 = QLabel(self.layoutWidget)
        self.label_9.setObjectName(u"label_9")

        self.gridLayout.addWidget(self.label_9, 0, 1, 1, 1)

        self.label_7 = QLabel(self.layoutWidget)
        self.label_7.setObjectName(u"label_7")

        self.gridLayout.addWidget(self.label_7, 0, 8, 1, 1)

        self.output_group = QPushButton(self.layoutWidget)
        self.output_group.setObjectName(u"output_group")

        self.gridLayout.addWidget(self.output_group, 2, 12, 1, 1)

        self.label_16 = QLabel(self.layoutWidget)
        self.label_16.setObjectName(u"label_16")

        self.gridLayout.addWidget(self.label_16, 0, 12, 1, 1)

        self.saveProtocol = QPushButton(protocols)
        self.saveProtocol.setObjectName(u"saveProtocol")
        self.saveProtocol.setGeometry(QRect(680, 540, 91, 24))
        self.saveProtocol.setStyleSheet(u"QPushButton\n"
"{\n"
"	color: rgb(34, 34, 34);\n"
"	background-color: rgb(162, 238, 255);\n"
"	border-color: rgb(255, 85, 0);\n"
"	border-radius: 12\n"
"}\n"
"QPushButton:\n"
"{\n"
"	background-color: Blue\n"
"}")
        self.removeStage = QPushButton(protocols)
        self.removeStage.setObjectName(u"removeStage")
        self.removeStage.setGeometry(QRect(30, 540, 75, 24))
        self.closeWindow = QPushButton(protocols)
        self.closeWindow.setObjectName(u"closeWindow")
        self.closeWindow.setGeometry(QRect(814, 540, 91, 24))
        self.label_12 = QLabel(protocols)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setGeometry(QRect(480, 60, 311, 16))

        self.retranslateUi(protocols)

        self.stim_type.setCurrentIndex(0)


        QMetaObject.connectSlotsByName(protocols)
    # setupUi

    def retranslateUi(self, protocols):
        protocols.setWindowTitle(QCoreApplication.translate("protocols", u"Form", None))
        self.label.setText(QCoreApplication.translate("protocols", u"Protocol designer", None))
        self.label_2.setText(QCoreApplication.translate("protocols", u"Number of cells", None))
        self.num_cells.setText("")
        self.label_4.setText(QCoreApplication.translate("protocols", u"Current protocol ", None))
        self.addStage.setText(QCoreApplication.translate("protocols", u"Add Stage", None))
        self.ncells.setText(QCoreApplication.translate("protocols", u"n cells", None))
        self.label_5.setText(QCoreApplication.translate("protocols", u"Repeats", None))
        self.label_6.setText(QCoreApplication.translate("protocols", u"Groups period \n"
" (ms) \n"
"", None))
        self.label_13.setText(QCoreApplication.translate("protocols", u"Light ON \n"
" time (ms)", None))
#if QT_CONFIG(whatsthis)
        self.label_10.setWhatsThis(QCoreApplication.translate("protocols", u"<html><head/><body><p>Add jitter to the stimulation sequence</p></body></html>", None))
#endif // QT_CONFIG(whatsthis)
        self.label_10.setText(QCoreApplication.translate("protocols", u"Jitter", None))
        self.stim_time.setText(QCoreApplication.translate("protocols", u"5", None))
#if QT_CONFIG(tooltip)
        self.groupsNumbers.setToolTip(QCoreApplication.translate("protocols", u"When \"Squares\" type, number of simultanous presented squares", None))
#endif // QT_CONFIG(tooltip)
        self.groupsNumbers.setText(QCoreApplication.translate("protocols", u"Number of \n"
" groups \n"
" or squares", None))
        self.groups_period.setText(QCoreApplication.translate("protocols", u"400", None))
        self.stim_type.setItemText(0, QCoreApplication.translate("protocols", u"Random", None))
        self.stim_type.setItemText(1, QCoreApplication.translate("protocols", u"Group only stim.", None))
        self.stim_type.setItemText(2, QCoreApplication.translate("protocols", u"Order", None))
        self.stim_type.setItemText(3, QCoreApplication.translate("protocols", u"Test", None))
        self.stim_type.setItemText(4, QCoreApplication.translate("protocols", u"Spontaneous", None))
        self.stim_type.setItemText(5, QCoreApplication.translate("protocols", u"Squares", None))

        self.jitter.setText("")
        self.label_11.setText(QCoreApplication.translate("protocols", u"Background \n"
" stimulation (Hz)", None))
        self.label_15.setText(QCoreApplication.translate("protocols", u"Probability \n"
" stimulation", None))
        self.repeats.setText("")
        self.label_3.setText(QCoreApplication.translate("protocols", u"Stage", None))
        self.on_time.setText(QCoreApplication.translate("protocols", u"5", None))
        self.groups_number.setText(QCoreApplication.translate("protocols", u"1", None))
        self.prob_stim.setText("")
        self.background_freq.setText(QCoreApplication.translate("protocols", u"1", None))
        self.group_size.setText(QCoreApplication.translate("protocols", u"12", None))
        self.label_8.setText(QCoreApplication.translate("protocols", u"Stimulation \n"
" time (min)", None))
        self.label_14.setText(QCoreApplication.translate("protocols", u"Is manual \n"
" groups", None))
        self.is_manual_sequence.setText("")
        self.label_9.setText(QCoreApplication.translate("protocols", u"Type", None))
        self.label_7.setText(QCoreApplication.translate("protocols", u"Group size \n"
" Square size", None))
        self.output_group.setText(QCoreApplication.translate("protocols", u"Output group", None))
        self.label_16.setText(QCoreApplication.translate("protocols", u"Press to define \n"
" output group", None))
        self.saveProtocol.setText(QCoreApplication.translate("protocols", u"Save Protocol", None))
        self.removeStage.setText(QCoreApplication.translate("protocols", u"Remove last", None))
        self.closeWindow.setText(QCoreApplication.translate("protocols", u"Close window", None))
        self.label_12.setText(QCoreApplication.translate("protocols", u"After change / update add new fields to protocol_design", None))
    # retranslateUi

