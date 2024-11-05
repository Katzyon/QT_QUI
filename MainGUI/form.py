<?xml version="1.0" encoding="UTF-8"?>
<ui version="4.0">
 <class>MainGui</class>
 <widget class="QMainWindow" name="MainGui">
  <property name="geometry">
   <rect>
    <x>0</x>
    <y>0</y>
    <width>1300</width>
    <height>671</height>
   </rect>
  </property>
  <property name="windowTitle">
   <string>MainGui</string>
  </property>
  <widget class="QWidget" name="centralwidget">
   <widget class="ImageView" name="imageview" native="true">
    <property name="geometry">
     <rect>
      <x>550</x>
      <y>10</y>
      <width>600</width>
      <height>600</height>
     </rect>
    </property>
   </widget>
   <widget class="QPushButton" name="snap">
    <property name="geometry">
     <rect>
      <x>450</x>
      <y>10</y>
      <width>75</width>
      <height>24</height>
     </rect>
    </property>
    <property name="text">
     <string>Snap</string>
    </property>
   </widget>
   <widget class="QPushButton" name="live">
    <property name="geometry">
     <rect>
      <x>450</x>
      <y>40</y>
      <width>75</width>
      <height>24</height>
     </rect>
    </property>
    <property name="text">
     <string>Live</string>
    </property>
   </widget>
   <widget class="QPushButton" name="DMD_Calibrate">
    <property name="geometry">
     <rect>
      <x>20</x>
      <y>550</y>
      <width>91</width>
      <height>24</height>
     </rect>
    </property>
    <property name="text">
     <string>Calibrate DMD</string>
    </property>
   </widget>
   <widget class="QPushButton" name="stop_movie">
    <property name="geometry">
     <rect>
      <x>450</x>
      <y>70</y>
      <width>75</width>
      <height>24</height>
     </rect>
    </property>
    <property name="text">
     <string>Stop Movie</string>
    </property>
   </widget>
   <widget class="QPushButton" name="mouse_shoot">
    <property name="geometry">
     <rect>
      <x>20</x>
      <y>580</y>
      <width>91</width>
      <height>24</height>
     </rect>
    </property>
    <property name="text">
     <string>click and light</string>
    </property>
   </widget>
   <widget class="QLineEdit" name="exposureT">
    <property name="geometry">
     <rect>
      <x>220</x>
      <y>30</y>
      <width>61</width>
      <height>22</height>
     </rect>
    </property>
   </widget>
   <widget class="QLabel" name="label">
    <property name="geometry">
     <rect>
      <x>108</x>
      <y>30</y>
      <width>81</width>
      <height>20</height>
     </rect>
    </property>
    <property name="text">
     <string>Exposure (ms)</string>
    </property>
   </widget>
   <widget class="QLabel" name="label_2">
    <property name="geometry">
     <rect>
      <x>110</x>
      <y>60</y>
      <width>49</width>
      <height>16</height>
     </rect>
    </property>
    <property name="text">
     <string>Binning</string>
    </property>
   </widget>
   <widget class="QComboBox" name="binning">
    <property name="geometry">
     <rect>
      <x>220</x>
      <y>60</y>
      <width>62</width>
      <height>22</height>
     </rect>
    </property>
    <item>
     <property name="text">
      <string>1x1</string>
     </property>
    </item>
    <item>
     <property name="text">
      <string>2x2</string>
     </property>
    </item>
   </widget>
  </widget>
  <widget class="QMenuBar" name="menubar">
   <property name="geometry">
    <rect>
     <x>0</x>
     <y>0</y>
     <width>1300</width>
     <height>22</height>
    </rect>
   </property>
   <widget class="QMenu" name="menuTab">
    <property name="title">
     <string>Tab</string>
    </property>
   </widget>
   <widget class="QMenu" name="menuTab2">
    <property name="title">
     <string>Tab2</string>
    </property>
   </widget>
   <addaction name="menuTab"/>
   <addaction name="menuTab2"/>
  </widget>
  <widget class="QStatusBar" name="statusbar"/>
 </widget>
 <customwidgets>
  <customwidget>
   <class>ImageView</class>
   <extends>QWidget</extends>
   <header location="global">pyqtgraph</header>
   <container>1</container>
  </customwidget>
 </customwidgets>
 <resources/>
 <connections/>
</ui>
