# -*- coding: utf-8 -*-

from PySide6.QtCore import QCoreApplication, QMetaObject, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialogButtonBox,
    QFrame,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QVBoxLayout,
    QWidget,
)


class Ui_protocols(object):
    def setupUi(self, protocols):
        if not protocols.objectName():
            protocols.setObjectName(u"protocols")
        protocols.resize(1280, 760)
        protocols.setMinimumSize(1100, 700)
        protocols.setStyleSheet(
            "QWidget { background-color: #f6f8fb; color: #1f2937; }"
            "QGroupBox {"
            "  font-weight: 600;"
            "  border: 1px solid #d8dee9;"
            "  border-radius: 8px;"
            "  margin-top: 14px;"
            "  padding-top: 12px;"
            "  background-color: #ffffff;"
            "}"
            "QGroupBox::title {"
            "  subcontrol-origin: margin;"
            "  left: 12px;"
            "  padding: 0 4px;"
            "}"
            "QLineEdit, QComboBox, QListWidget {"
            "  border: 1px solid #c7d0dd;"
            "  border-radius: 6px;"
            "  padding: 6px 8px;"
            "  background-color: #ffffff;"
            "}"
            "QPushButton {"
            "  border: 1px solid #b7c3d4;"
            "  border-radius: 6px;"
            "  padding: 7px 12px;"
            "  background-color: #eef3f9;"
            "}"
            "QPushButton:hover { background-color: #e3ebf5; }"
            "QPushButton#saveProtocol {"
            "  background-color: #0f766e;"
            "  color: white;"
            "  border-color: #0f766e;"
            "}"
            "QPushButton#saveProtocol:hover { background-color: #115e59; }"
            "QListWidget { padding: 4px; }"
            "QLabel#sectionHint { color: #6b7280; }"
            "QFrame#summaryCard {"
            "  background-color: #eef6ff;"
            "  border: 1px solid #cfe0f5;"
            "  border-radius: 8px;"
            "}"
        )

        self.mainLayout = QVBoxLayout(protocols)
        self.mainLayout.setObjectName(u"mainLayout")
        self.mainLayout.setContentsMargins(18, 18, 18, 18)
        self.mainLayout.setSpacing(14)

        self.headerLayout = QHBoxLayout()
        self.headerLayout.setSpacing(16)

        self.headerTextLayout = QVBoxLayout()
        self.headerTextLayout.setSpacing(4)

        self.label = QLabel(protocols)
        self.label.setObjectName(u"label")
        title_font = QFont()
        title_font.setPointSize(15)
        title_font.setBold(True)
        self.label.setFont(title_font)
        self.headerTextLayout.addWidget(self.label)

        self.label_12 = QLabel(protocols)
        self.label_12.setObjectName(u"label_12")
        self.label_12.setWordWrap(True)
        self.label_12.setProperty("class", "sectionHint")
        self.label_12.setObjectName(u"sectionHint")
        self.headerTextLayout.addWidget(self.label_12)

        self.headerLayout.addLayout(self.headerTextLayout, 1)

        self.summaryCard = QFrame(protocols)
        self.summaryCard.setObjectName(u"summaryCard")
        self.summaryLayout = QVBoxLayout(self.summaryCard)
        self.summaryLayout.setContentsMargins(14, 10, 14, 10)
        self.summaryLayout.setSpacing(2)

        self.label_2 = QLabel(self.summaryCard)
        self.label_2.setObjectName(u"label_2")
        self.summaryLayout.addWidget(self.label_2)

        self.ncells = QLabel(self.summaryCard)
        self.ncells.setObjectName(u"ncells")
        cells_font = QFont()
        cells_font.setPointSize(16)
        cells_font.setBold(True)
        self.ncells.setFont(cells_font)
        self.summaryLayout.addWidget(self.ncells)

        self.num_cells = QLabel(self.summaryCard)
        self.num_cells.setObjectName(u"num_cells")
        self.num_cells.hide()
        self.summaryLayout.addWidget(self.num_cells)

        self.headerLayout.addWidget(self.summaryCard, 0)
        self.mainLayout.addLayout(self.headerLayout)

        self.contentLayout = QHBoxLayout()
        self.contentLayout.setSpacing(14)

        self.controlsColumn = QVBoxLayout()
        self.controlsColumn.setSpacing(12)

        self.coreSettingsBox = QGroupBox(protocols)
        self.coreSettingsBox.setObjectName(u"coreSettingsBox")
        self.coreSettingsLayout = QGridLayout(self.coreSettingsBox)
        self.coreSettingsLayout.setHorizontalSpacing(12)
        self.coreSettingsLayout.setVerticalSpacing(10)

        self.label_3 = QLabel(self.coreSettingsBox)
        self.label_3.setObjectName(u"label_3")
        self.coreSettingsLayout.addWidget(self.label_3, 0, 0)

        self.stim_type = QComboBox(self.coreSettingsBox)
        self.stim_type.setObjectName(u"stim_type")
        self.stim_type.addItem("")
        self.stim_type.addItem("")
        self.stim_type.addItem("")
        self.stim_type.addItem("")
        self.stim_type.addItem("")
        self.stim_type.addItem("")
        self.stim_type.addItem("")
        self.coreSettingsLayout.addWidget(self.stim_type, 0, 1)

        self.label_13 = QLabel(self.coreSettingsBox)
        self.label_13.setObjectName(u"label_13")
        self.coreSettingsLayout.addWidget(self.label_13, 0, 2)

        self.on_time = QLineEdit(self.coreSettingsBox)
        self.on_time.setObjectName(u"on_time")
        self.coreSettingsLayout.addWidget(self.on_time, 0, 3)

        self.label_11 = QLabel(self.coreSettingsBox)
        self.label_11.setObjectName(u"label_11")
        self.coreSettingsLayout.addWidget(self.label_11, 1, 0)

        self.background_freq = QLineEdit(self.coreSettingsBox)
        self.background_freq.setObjectName(u"background_freq")
        self.coreSettingsLayout.addWidget(self.background_freq, 1, 1)

        self.label_8 = QLabel(self.coreSettingsBox)
        self.label_8.setObjectName(u"label_8")
        self.coreSettingsLayout.addWidget(self.label_8, 1, 2)

        self.stim_time = QLineEdit(self.coreSettingsBox)
        self.stim_time.setObjectName(u"stim_time")
        self.coreSettingsLayout.addWidget(self.stim_time, 1, 3)

        self.label_10 = QLabel(self.coreSettingsBox)
        self.label_10.setObjectName(u"label_10")
        self.coreSettingsLayout.addWidget(self.label_10, 2, 0)

        self.jitter = QCheckBox(self.coreSettingsBox)
        self.jitter.setObjectName(u"jitter")
        self.coreSettingsLayout.addWidget(self.jitter, 2, 1)

        self.label_15 = QLabel(self.coreSettingsBox)
        self.label_15.setObjectName(u"label_15")
        self.coreSettingsLayout.addWidget(self.label_15, 2, 2)

        self.prob_stim = QCheckBox(self.coreSettingsBox)
        self.prob_stim.setObjectName(u"prob_stim")
        self.coreSettingsLayout.addWidget(self.prob_stim, 2, 3)

        self.label_19 = QLabel(self.coreSettingsBox)
        self.label_19.setObjectName(u"label_19")
        self.coreSettingsLayout.addWidget(self.label_19, 3, 0)

        self.stdp_dt = QLineEdit(self.coreSettingsBox)
        self.stdp_dt.setObjectName(u"stdp_dt")
        self.coreSettingsLayout.addWidget(self.stdp_dt, 3, 1)

        self.label_20 = QLabel(self.coreSettingsBox)
        self.label_20.setObjectName(u"label_20")
        self.coreSettingsLayout.addWidget(self.label_20, 3, 2)

        self.stdp_ipi = QLineEdit(self.coreSettingsBox)
        self.stdp_ipi.setObjectName(u"stdp_ipi")
        self.coreSettingsLayout.addWidget(self.stdp_ipi, 3, 3)

        self.controlsColumn.addWidget(self.coreSettingsBox)

        self.groupSettingsBox = QGroupBox(protocols)
        self.groupSettingsBox.setObjectName(u"groupSettingsBox")
        self.groupSettingsLayout = QGridLayout(self.groupSettingsBox)
        self.groupSettingsLayout.setHorizontalSpacing(12)
        self.groupSettingsLayout.setVerticalSpacing(10)

        self.label_6 = QLabel(self.groupSettingsBox)
        self.label_6.setObjectName(u"label_6")
        self.groupSettingsLayout.addWidget(self.label_6, 0, 0)

        self.groups_period = QLineEdit(self.groupSettingsBox)
        self.groups_period.setObjectName(u"groups_period")
        self.groupSettingsLayout.addWidget(self.groups_period, 0, 1)

        self.label_7 = QLabel(self.groupSettingsBox)
        self.label_7.setObjectName(u"label_7")
        self.groupSettingsLayout.addWidget(self.label_7, 0, 2)

        self.group_size = QLineEdit(self.groupSettingsBox)
        self.group_size.setObjectName(u"group_size")
        self.groupSettingsLayout.addWidget(self.group_size, 0, 3)

        self.groupsNumbers = QLabel(self.groupSettingsBox)
        self.groupsNumbers.setObjectName(u"groupsNumbers")
        self.groupSettingsLayout.addWidget(self.groupsNumbers, 1, 0)

        self.groups_number = QLineEdit(self.groupSettingsBox)
        self.groups_number.setObjectName(u"groups_number")
        self.groupSettingsLayout.addWidget(self.groups_number, 1, 1)

        self.label_14 = QLabel(self.groupSettingsBox)
        self.label_14.setObjectName(u"label_14")
        self.groupSettingsLayout.addWidget(self.label_14, 1, 2)

        self.is_manual_sequence = QCheckBox(self.groupSettingsBox)
        self.is_manual_sequence.setObjectName(u"is_manual_sequence")
        self.groupSettingsLayout.addWidget(self.is_manual_sequence, 1, 3)

        self.label_16 = QLabel(self.groupSettingsBox)
        self.label_16.setObjectName(u"label_16")
        self.groupSettingsLayout.addWidget(self.label_16, 2, 0, 1, 2)

        self.output_group = QPushButton(self.groupSettingsBox)
        self.output_group.setObjectName(u"output_group")
        self.groupSettingsLayout.addWidget(self.output_group, 2, 2, 1, 2)

        self.controlsColumn.addWidget(self.groupSettingsBox)

        self.roiSettingsBox = QGroupBox(protocols)
        self.roiSettingsBox.setObjectName(u"roiSettingsBox")
        self.roiSettingsLayout = QVBoxLayout(self.roiSettingsBox)
        self.roiSettingsLayout.setSpacing(10)

        self.roiToggleLayout = QHBoxLayout()
        self.roiToggleLayout.setSpacing(8)

        self.label_17 = QLabel(self.roiSettingsBox)
        self.label_17.setObjectName(u"label_17")
        self.roiToggleLayout.addWidget(self.label_17)

        self.use_roi = QCheckBox(self.roiSettingsBox)
        self.use_roi.setObjectName(u"use_roi")
        self.roiToggleLayout.addWidget(self.use_roi)
        self.roiToggleLayout.addStretch(1)
        self.roiSettingsLayout.addLayout(self.roiToggleLayout)

        self.roiModePanel = QFrame(self.roiSettingsBox)
        self.roiModePanel.setObjectName(u"roiModePanel")
        self.roiModePanel.setStyleSheet(
            "QFrame#roiModePanel {"
            "  background-color: #f8fbff;"
            "  border: 1px solid #d7e6f7;"
            "  border-radius: 6px;"
            "}"
        )
        self.roiModePanelLayout = QGridLayout(self.roiModePanel)
        self.roiModePanelLayout.setContentsMargins(10, 10, 10, 10)
        self.roiModePanelLayout.setHorizontalSpacing(10)
        self.roiModePanelLayout.setVerticalSpacing(8)

        self.roi_mode_hint = QLabel(self.roiModePanel)
        self.roi_mode_hint.setObjectName(u"roi_mode_hint")
        self.roi_mode_hint.setWordWrap(True)
        self.roiModePanelLayout.addWidget(self.roi_mode_hint, 0, 0, 1, 2)

        self.roi_presentation_label = QLabel(self.roiModePanel)
        self.roi_presentation_label.setObjectName(u"roi_presentation_label")
        self.roiModePanelLayout.addWidget(self.roi_presentation_label, 1, 0)

        self.roi_presentation_mode = QComboBox(self.roiModePanel)
        self.roi_presentation_mode.setObjectName(u"roi_presentation_mode")
        self.roi_presentation_mode.addItem("")
        self.roi_presentation_mode.addItem("")
        self.roiModePanelLayout.addWidget(self.roi_presentation_mode, 1, 1)

        self.roiModePanel.setVisible(False)
        self.roiSettingsLayout.addWidget(self.roiModePanel)

        self.controlsColumn.addWidget(self.roiSettingsBox)

        self.recordingBox = QGroupBox(protocols)
        self.recordingBox.setObjectName(u"recordingBox")
        self.recordingLayout = QGridLayout(self.recordingBox)
        self.recordingLayout.setHorizontalSpacing(12)
        self.recordingLayout.setVerticalSpacing(10)

        self.label_5 = QLabel(self.recordingBox)
        self.label_5.setObjectName(u"label_5")
        self.recordingLayout.addWidget(self.label_5, 0, 0)

        self.record_stage = QCheckBox(self.recordingBox)
        self.record_stage.setObjectName(u"record_stage")
        self.recordingLayout.addWidget(self.record_stage, 0, 1)

        self.label_18 = QLabel(self.recordingBox)
        self.label_18.setObjectName(u"label_18")
        self.recordingLayout.addWidget(self.label_18, 0, 2)

        self.record_raw = QCheckBox(self.recordingBox)
        self.record_raw.setObjectName(u"record_raw")
        self.recordingLayout.addWidget(self.record_raw, 0, 3)

        self.controlsColumn.addWidget(self.recordingBox)
        self.controlsColumn.addItem(QSpacerItem(20, 20, QSizePolicy.Minimum, QSizePolicy.Expanding))

        self.contentLayout.addLayout(self.controlsColumn, 3)

        self.previewColumn = QVBoxLayout()
        self.previewColumn.setSpacing(10)

        self.label_4 = QLabel(protocols)
        self.label_4.setObjectName(u"label_4")
        list_title_font = QFont()
        list_title_font.setPointSize(11)
        list_title_font.setBold(True)
        self.label_4.setFont(list_title_font)
        self.previewColumn.addWidget(self.label_4)

        self.protocolHint = QLabel(protocols)
        self.protocolHint.setObjectName(u"protocolHint")
        self.protocolHint.setWordWrap(True)
        self.protocolHint.setStyleSheet("color: #6b7280;")
        self.previewColumn.addWidget(self.protocolHint)

        self.listWidget = QListWidget(protocols)
        self.listWidget.setObjectName(u"listWidget")
        self.previewColumn.addWidget(self.listWidget, 1)

        self.stageActionsLayout = QHBoxLayout()
        self.stageActionsLayout.setSpacing(8)

        self.addStage = QPushButton(protocols)
        self.addStage.setObjectName(u"addStage")
        self.stageActionsLayout.addWidget(self.addStage)

        self.removeStage = QPushButton(protocols)
        self.removeStage.setObjectName(u"removeStage")
        self.stageActionsLayout.addWidget(self.removeStage)

        self.stageActionsLayout.addStretch(1)
        self.previewColumn.addLayout(self.stageActionsLayout)

        self.contentLayout.addLayout(self.previewColumn, 4)
        self.mainLayout.addLayout(self.contentLayout, 1)

        self.footerLine = QFrame(protocols)
        self.footerLine.setFrameShape(QFrame.HLine)
        self.footerLine.setFrameShadow(QFrame.Sunken)
        self.mainLayout.addWidget(self.footerLine)

        self.footerLayout = QHBoxLayout()
        self.footerLayout.setSpacing(8)
        self.footerLayout.addStretch(1)

        self.closeWindow = QPushButton(protocols)
        self.closeWindow.setObjectName(u"closeWindow")
        self.footerLayout.addWidget(self.closeWindow)

        self.saveProtocol = QPushButton(protocols)
        self.saveProtocol.setObjectName(u"saveProtocol")
        self.footerLayout.addWidget(self.saveProtocol)

        self.mainLayout.addLayout(self.footerLayout)

        self.retranslateUi(protocols)
        self.stim_type.setCurrentIndex(0)
        self.use_roi.toggled.connect(self.roiModePanel.setVisible)

        QMetaObject.connectSlotsByName(protocols)

    def retranslateUi(self, protocols):
        protocols.setWindowTitle(QCoreApplication.translate("protocols", u"Protocol Designer", None))
        self.label.setText(QCoreApplication.translate("protocols", u"Protocol designer", None))
        self.label_12.setText(QCoreApplication.translate(
            "protocols",
            u"Group related settings into sections, keep stage editing on the left, and keep the protocol preview and actions together on the right.",
            None,
        ))
        self.label_2.setText(QCoreApplication.translate("protocols", u"Number of cells", None))
        self.ncells.setText(QCoreApplication.translate("protocols", u"0", None))
        self.num_cells.setText("")

        self.coreSettingsBox.setTitle(QCoreApplication.translate("protocols", u"Stage timing", None))
        self.label_3.setText(QCoreApplication.translate("protocols", u"Type", None))
        self.stim_type.setItemText(0, QCoreApplication.translate("protocols", u"Random", None))
        self.stim_type.setItemText(1, QCoreApplication.translate("protocols", u"Group only stim.", None))
        self.stim_type.setItemText(2, QCoreApplication.translate("protocols", u"Order", None))
        self.stim_type.setItemText(3, QCoreApplication.translate("protocols", u"Test", None))
        self.stim_type.setItemText(4, QCoreApplication.translate("protocols", u"Spontaneous", None))
        self.stim_type.setItemText(5, QCoreApplication.translate("protocols", u"Squares", None))
        self.stim_type.setItemText(6, QCoreApplication.translate("protocols", u"STDP", None))
        self.label_13.setText(QCoreApplication.translate("protocols", u"Light ON time (ms)", None))
        self.on_time.setText(QCoreApplication.translate("protocols", u"5", None))
        self.label_11.setText(QCoreApplication.translate("protocols", u"Background stimulation (Hz)", None))
        self.background_freq.setText(QCoreApplication.translate("protocols", u"1", None))
        self.label_8.setText(QCoreApplication.translate("protocols", u"Stimulation time (min)", None))
        self.stim_time.setText(QCoreApplication.translate("protocols", u"5", None))
        self.label_10.setText(QCoreApplication.translate("protocols", u"Add jitter", None))
        self.jitter.setText(QCoreApplication.translate("protocols", u"Enabled", None))
        self.label_15.setText(QCoreApplication.translate("protocols", u"Probability stimulation", None))
        self.prob_stim.setText(QCoreApplication.translate("protocols", u"Enabled", None))
        self.label_19.setText(QCoreApplication.translate("protocols", u"STDP dt (ms)", None))
        self.stdp_dt.setText(QCoreApplication.translate("protocols", u"10", None))
        self.label_20.setText(QCoreApplication.translate("protocols", u"STDP IPI (ms)", None))
        self.stdp_ipi.setText(QCoreApplication.translate("protocols", u"400", None))

        self.groupSettingsBox.setTitle(QCoreApplication.translate("protocols", u"Grouping", None))
        self.label_6.setText(QCoreApplication.translate("protocols", u"Groups period (ms)", None))
        self.groups_period.setText(QCoreApplication.translate("protocols", u"400", None))
        self.label_7.setText(QCoreApplication.translate("protocols", u"Group size / square size", None))
        self.group_size.setText(QCoreApplication.translate("protocols", u"12", None))
        self.groupsNumbers.setText(QCoreApplication.translate("protocols", u"Number of groups or squares", None))
        self.groupsNumbers.setToolTip(QCoreApplication.translate("protocols", u"When \"Squares\" type, number of simultaneous presented squares", None))
        self.groups_number.setText(QCoreApplication.translate("protocols", u"1", None))
        self.label_14.setText(QCoreApplication.translate("protocols", u"Manual groups", None))
        self.is_manual_sequence.setText(QCoreApplication.translate("protocols", u"Use manual sequence", None))
        self.label_16.setText(QCoreApplication.translate("protocols", u"Choose cells that should remain outside patterned stimulation", None))
        self.output_group.setText(QCoreApplication.translate("protocols", u"Output group", None))

        self.roiSettingsBox.setTitle(QCoreApplication.translate("protocols", u"ROI stimulation", None))
        self.label_17.setText(QCoreApplication.translate("protocols", u"Use user's ROI", None))
        self.use_roi.setText(QCoreApplication.translate("protocols", u"Enable ROI-based stimulation", None))
        self.roi_mode_hint.setText(QCoreApplication.translate("protocols", u"ROI presentation is only relevant when ROI stimulation is enabled.", None))
        self.roi_presentation_label.setText(QCoreApplication.translate("protocols", u"ROI presentation", None))
        self.roi_presentation_mode.setItemText(0, QCoreApplication.translate("protocols", u"Sequential", None))
        self.roi_presentation_mode.setItemText(1, QCoreApplication.translate("protocols", u"Simultaneous", None))

        self.recordingBox.setTitle(QCoreApplication.translate("protocols", u"Recording", None))
        self.label_5.setText(QCoreApplication.translate("protocols", u"Record stage", None))
        self.record_stage.setText(QCoreApplication.translate("protocols", u"Enabled", None))
        self.label_18.setText(QCoreApplication.translate("protocols", u"Record raw data", None))
        self.record_raw.setText(QCoreApplication.translate("protocols", u"Enabled", None))

        self.label_4.setText(QCoreApplication.translate("protocols", u"Current protocol", None))
        self.protocolHint.setText(QCoreApplication.translate("protocols", u"Each added stage appears here so the final sequence is easy to review before saving.", None))
        self.addStage.setText(QCoreApplication.translate("protocols", u"Add stage", None))
        self.removeStage.setText(QCoreApplication.translate("protocols", u"Remove last", None))
        self.closeWindow.setText(QCoreApplication.translate("protocols", u"Close window", None))
        self.saveProtocol.setText(QCoreApplication.translate("protocols", u"Save protocol", None))
