import os
from glob import glob
import unittest
from collections import OrderedDict
import numpy as np
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging


IMAGE_PATTERNS = [
    'T1-postcontrast.nii',
    'T2.nii',
    'FLAIR.nii',
    'T1-precontrast.nii'
]
LABEL_PATTERN = 'tumor-seg-CW.nii'
LABEL_NAMES = {
    1: 'necrotic / non-enhancing core',
    2: 'peritumoral edema',
    3: 'enhancing tumor'
}
LABEL_COLORS = {
    1: (255,0,0),
    2: (0,255,0),
    3: (0,0,255)
}

LABEL_NAME_TO_LABEL_VAL = {val: key for key, val in LABEL_NAMES.items()}


class BatchSegmenter(ScriptedLoadableModule):

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Batch Segmentation Editor"
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["Brian Keating (Cortechs.ai)"]
        self.parent.helpText = """"""
        self.parent.helpText += self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = """"""


class BatchSegmenterWidget(ScriptedLoadableModuleWidget):

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        

        #### Data Area ####

        dataCollapsibleButton = ctk.ctkCollapsibleButton()
        dataCollapsibleButton.text = 'Select Data'
        self.layout.addWidget(dataCollapsibleButton)

        # Layout within the collapsible button
        dataFormLayout = qt.QFormLayout(dataCollapsibleButton)

        # Select data Button
        self.selectDataButton = qt.QPushButton('Select Data Folders')
        self.selectDataButton.toolTip = 'Select directory containing nifti/mgz files.'
        self.selectDataButton.enabled = True
        dataFormLayout.addRow(qt.QLabel('Folder Names:'), self.selectDataButton)

        # Combobox to display selected folders
        self.caseComboBox = qt.QComboBox()
        self.caseComboBox.enabled = False
        dataFormLayout.addRow(qt.QLabel('Active Folder:'), self.caseComboBox)

        # Navigate images buttons
        navigateImagesLayout = qt.QHBoxLayout()
        self.previousImageButton = qt.QPushButton('Previous Image')
        self.previousImageButton.enabled = False
        navigateImagesLayout.addWidget(self.previousImageButton)

        self.nextImageButton = qt.QPushButton('Next Image')
        self.nextImageButton.enabled = False
        navigateImagesLayout.addWidget(self.nextImageButton)
        dataFormLayout.addRow(navigateImagesLayout)

        #### Segmentation Area ####

        self.segCollapsibleButton = ctk.ctkCollapsibleButton()
        self.segCollapsibleButton.text = 'Segmentation'
        self.segCollapsibleButton.collapsed = False
        self.layout.addWidget(self.segCollapsibleButton)

        # Layout within the dummy collapsible button
        segFormLayout = qt.QFormLayout(self.segCollapsibleButton)
        self.segEditorWidget = slicer.qMRMLSegmentEditorWidget()
        self.segEditorWidget.setMRMLScene(slicer.mrmlScene)
        segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
        slicer.mrmlScene.AddNode(segmentEditorNode)
        self.segEditorWidget.setMRMLSegmentEditorNode(segmentEditorNode)
        self.segEditorWidget.enabled = True
        self.segEditorWidget.setSwitchToSegmentationsButtonVisible(False)
        self.segEditorWidget.setSegmentationNodeSelectorVisible(False)
        self.segEditorWidget.setMasterVolumeNodeSelectorVisible(False)
        self.segEditorWidget.setReadOnly(False)
        segFormLayout.addRow(self.segEditorWidget)

        ## Add vertical spacer to keep widgets near top
        self.layout.addStretch(1)
        
        ### connections ###
        self.selectDataButton.clicked.connect(self.onSelectDataButtonPressed)
        self.previousImageButton.connect('clicked(bool)', self.previousImage)
        self.nextImageButton.connect('clicked(bool)', self.nextImage)
        self.caseComboBox.connect('currentIndexChanged(const QString&)', self.onComboboxChanged)

        ### Logic ###
        self.image_label_dict = OrderedDict()
        self.selected_image_ind = None
        self.active_label_fn = None
        self.dataFolders = None

        # DEBUG
        self.image_label_dict = OrderedDict([(u'PGBM-001_11-19-1991', ([u'/Users/brian/tmp/williamson-segs/images/PGBM-001_11-19-1991/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-001_11-19-1991/T2.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-001_11-19-1991/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-001_11-19-1991/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/PGBM-001_11-19-1991/tumor-seg-CW.nii')), (u'PGBM-005_07-02-1991', ([u'/Users/brian/tmp/williamson-segs/images/PGBM-005_07-02-1991/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-005_07-02-1991/T2.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-005_07-02-1991/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-005_07-02-1991/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/PGBM-005_07-02-1991/tumor-seg-CW.nii')), (u'PGBM-010_05-20-1992', ([u'/Users/brian/tmp/williamson-segs/images/PGBM-010_05-20-1992/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-010_05-20-1992/T2.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-010_05-20-1992/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-010_05-20-1992/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/PGBM-010_05-20-1992/tumor-seg-CW.nii')), (u'PGBM-010_06-18-1992', ([u'/Users/brian/tmp/williamson-segs/images/PGBM-010_06-18-1992/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-010_06-18-1992/T2.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-010_06-18-1992/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-010_06-18-1992/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/PGBM-010_06-18-1992/tumor-seg-CW.nii')), (u'PGBM-011_06-29-1989', ([u'/Users/brian/tmp/williamson-segs/images/PGBM-011_06-29-1989/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-011_06-29-1989/T2.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-011_06-29-1989/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-011_06-29-1989/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/PGBM-011_06-29-1989/tumor-seg-CW.nii')), (u'PGBM-011_08-24-1989', ([u'/Users/brian/tmp/williamson-segs/images/PGBM-011_08-24-1989/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-011_08-24-1989/T2.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-011_08-24-1989/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/PGBM-011_08-24-1989/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/PGBM-011_08-24-1989/tumor-seg-CW.nii')), (u'TCGA-02-0003_06-07-1997', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-02-0003_06-07-1997/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-02-0003_06-07-1997/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-02-0003_06-07-1997/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-02-0003_06-07-1997/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-02-0003_06-07-1997/tumor-seg-CW.nii')), (u'TCGA-02-0048_01-28-1999', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-02-0048_01-28-1999/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-02-0048_01-28-1999/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-02-0048_01-28-1999/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-02-0048_01-28-1999/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-02-0048_01-28-1999/tumor-seg-CW.nii')), (u'TCGA-02-0060_02-27-2000', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-02-0060_02-27-2000/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-02-0060_02-27-2000/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-02-0060_02-27-2000/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-02-0060_02-27-2000/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-02-0060_02-27-2000/tumor-seg-CW.nii')), (u'TCGA-12-1602_03-04-2001', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-12-1602_03-04-2001/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-12-1602_03-04-2001/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-12-1602_03-04-2001/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-12-1602_03-04-2001/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-12-1602_03-04-2001/tumor-seg-CW.nii')), (u'TCGA-14-0813_10-12-1996', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-14-0813_10-12-1996/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-14-0813_10-12-1996/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-14-0813_10-12-1996/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-14-0813_10-12-1996/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-14-0813_10-12-1996/tumor-seg-CW.nii')), (u'TCGA-14-1402_10-08-1999', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-14-1402_10-08-1999/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-14-1402_10-08-1999/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-14-1402_10-08-1999/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-14-1402_10-08-1999/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-14-1402_10-08-1999/tumor-seg-CW.nii')), (u'TCGA-14-1829_06-16-2001', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-14-1829_06-16-2001/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-14-1829_06-16-2001/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-14-1829_06-16-2001/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-14-1829_06-16-2001/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-14-1829_06-16-2001/tumor-seg-CW.nii')), (u'TCGA-CS-4943_09-02-2000', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-4943_09-02-2000/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-4943_09-02-2000/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-4943_09-02-2000/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-4943_09-02-2000/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-4943_09-02-2000/tumor-seg-CW.nii')), (u'TCGA-CS-5395_10-04-1998', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-5395_10-04-1998/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-5395_10-04-1998/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-5395_10-04-1998/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-5395_10-04-1998/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-5395_10-04-1998/tumor-seg-CW.nii')), (u'TCGA-CS-6290_09-17-2000', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-6290_09-17-2000/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-6290_09-17-2000/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-6290_09-17-2000/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-6290_09-17-2000/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-6290_09-17-2000/tumor-seg-CW.nii')), (u'TCGA-CS-6667_11-05-2001', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-6667_11-05-2001/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-6667_11-05-2001/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-6667_11-05-2001/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-6667_11-05-2001/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-CS-6667_11-05-2001/tumor-seg-CW.nii')), (u'TCGA-DU-6407_12-22-1992', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-DU-6407_12-22-1992/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-DU-6407_12-22-1992/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-DU-6407_12-22-1992/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-DU-6407_12-22-1992/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-DU-6407_12-22-1992/tumor-seg-CW.nii')), (u'TCGA-DU-6410_12-28-1995', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-DU-6410_12-28-1995/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-DU-6410_12-28-1995/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-DU-6410_12-28-1995/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-DU-6410_12-28-1995/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-DU-6410_12-28-1995/tumor-seg-CW.nii')), (u'TCGA-EZ-7264A_08-16-2001', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-EZ-7264A_08-16-2001/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-EZ-7264A_08-16-2001/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-EZ-7264A_08-16-2001/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-EZ-7264A_08-16-2001/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-EZ-7264A_08-16-2001/tumor-seg-CW.nii')), (u'TCGA-HT-7692_07-24-1996', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-7692_07-24-1996/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-7692_07-24-1996/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-7692_07-24-1996/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-7692_07-24-1996/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-7692_07-24-1996/tumor-seg-CW.nii')), (u'TCGA-HT-7855_10-20-1995', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-7855_10-20-1995/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-7855_10-20-1995/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-7855_10-20-1995/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-7855_10-20-1995/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-7855_10-20-1995/tumor-seg-CW.nii')), (u'TCGA-HT-7860_05-13-1996', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-7860_05-13-1996/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-7860_05-13-1996/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-7860_05-13-1996/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-7860_05-13-1996/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-7860_05-13-1996/tumor-seg-CW.nii')), (u'TCGA-HT-8106_07-28-1997', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-8106_07-28-1997/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-8106_07-28-1997/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-8106_07-28-1997/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-8106_07-28-1997/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-8106_07-28-1997/tumor-seg-CW.nii')), (u'TCGA-HT-A614_12-24-1999', ([u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-A614_12-24-1999/T1-postcontrast.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-A614_12-24-1999/T2.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-A614_12-24-1999/FLAIR.nii', u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-A614_12-24-1999/T1-precontrast.nii'], u'/Users/brian/tmp/williamson-segs/images/TCGA-HT-A614_12-24-1999/tumor-seg-CW.nii'))])
        self.updateWidgets()


    def onSelectDataButtonPressed(self):
        file_dialog = qt.QFileDialog(None, 'Select Data Folders')
        file_dialog.setFileMode(qt.QFileDialog.DirectoryOnly)
        file_dialog.setOption(qt.QFileDialog.DontUseNativeDialog, True)
        file_dialog.setOption(qt.QFileDialog.ShowDirsOnly, True)
        file_view = file_dialog.findChild(qt.QListView, 'listView')
        # make it possible to select multiple directories:
        if file_view:
            file_view.setSelectionMode(qt.QAbstractItemView.MultiSelection)
        f_tree_view = file_dialog.findChild(qt.QTreeView)
        if f_tree_view:
            f_tree_view.setSelectionMode(qt.QAbstractItemView.MultiSelection)
        if file_dialog.exec_():
            data_folders = file_dialog.selectedFiles()
            self.image_label_dict = OrderedDict()
            for data_folder in data_folders:
                folder_ims = [glob(os.path.join(data_folder, im_fn)) for im_fn in IMAGE_PATTERNS]
                has_required_ims = all(len(ims)==1 for ims in folder_ims)
                has_label = len(glob(os.path.join(data_folder, LABEL_PATTERN))) == 1
                if has_required_ims and has_label:
                    folder_name = os.path.basename(data_folder)
                    im_fns = [ims[0] for ims in folder_ims]
                    label_fn = glob(os.path.join(data_folder, LABEL_PATTERN))[0]
                    self.image_label_dict[folder_name] = im_fns, label_fn
                else:
                    print('WARNING: Skipping '+data_folder+' because it is missing (or contains multiple) required input images')
            print(self.image_label_dict)
            self.updateWidgets()


    def updateWidgets(self):
        """Load selected valid case names into the widget"""
        # select data button
        if len(self.image_label_dict) > 1:
            self.selectDataButton.setText(str(len(self.image_label_dict))+' cases')
        elif len(self.image_label_dict) == 1:
            self.selectDataButton.setText(os.path.basename(list(self.image_label_dict.keys())[0]))
        
        # case combobox
        self.caseComboBox.clear()
        if self.image_label_dict:
            case_names = list(self.image_label_dict.keys())
            self.caseComboBox.addItems(case_names)  # load names into combobox
            self.caseComboBox.enabled = True
            self.nextImageButton.enabled = True
            self.previousImageButton.enabled = True
            self.selected_image_ind = 0
        else:
            self.selectDataButton.setText('Select Data Folders')
            self.caseComboBox.enabled = False
            self.nextImageButton.enabled = False
            self.previousImageButton.enabled = False
            self.selected_image_ind = None
            self.active_label_fn = None


    def nextImage(self):
        self.selected_image_ind += 1
        if self.selected_image_ind > len(self.image_label_dict) - 1:
            self.selected_image_ind -= len(self.image_label_dict)
        self.caseComboBox.setCurrentIndex(self.selected_image_ind)


    def previousImage(self):
        self.selected_image_ind -= 1
        if self.selected_image_ind < 0:
            self.selected_image_ind += len(self.image_label_dict)
        self.caseComboBox.setCurrentIndex(self.selected_image_ind)


    def onComboboxChanged(self, text):
        
        if not self.image_label_dict:
            return

        # save old seg before loading the new one
        self.saveActiveSegmentation()
        try:
            self.selected_image_ind = list(self.image_label_dict.keys()).index(text)
        except ValueError:
            return

        try:
            im_fns, label_fn = self.image_label_dict[text]
        except KeyError:
            print('Could not find %s among selected images' % text)
            return
        self.active_label_fn = label_fn

        # remove existing nodes (if any)
        if hasattr(self, 'volNodes'):
            for volNode in self.volNodes:
                slicer.mrmlScene.RemoveNode(volNode)
        if hasattr(self, 'segmentationNode'):
            slicer.mrmlScene.RemoveNode(self.segmentationNode)
        
        # TODO: if there's not label_fn, create empty seg
        
        # set red/green/yellow views to axial orientation
        sliceNodes = slicer.util.getNodesByClass('vtkMRMLSliceNode')
        for sliceNode in sliceNodes:
            sliceNode.SetOrientationToAxial()

        # create label node as a labelVolume
        [success, labelmapNode] = slicer.util.loadLabelVolume(label_fn, returnNode=True)
        if not success:
            print('Failed to load label volume ', label_fn)
            return
                
        # create vol nodes
        self.volNodes = []
        for im_fn in im_fns:
            [success, vol_node] = slicer.util.loadVolume(im_fn, returnNode=True)
            vol_node.GetScalarVolumeDisplayNode().SetInterpolate(0)
            if success:
                self.volNodes.append(vol_node)
            else:
                print('WARNING: Failed to load volume ', im_fn)
        if len(self.volNodes) == 0:
            print('Failed to load any volumes from folder '+text+'!')
            return

        # create segmentation node from labelVolume
        self.segmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode', 'Tumor Segmentation')
        self.segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(self.volNodes[0])
        self.segmentationNode.CreateDefaultDisplayNodes()
        slicer.mrmlScene.AddNode(self.segmentationNode)
        slicer.vtkSlicerSegmentationsModuleLogic.ImportLabelmapToSegmentationNode(labelmapNode, self.segmentationNode)
        self.segEditorWidget.setSegmentationNode(self.segmentationNode) 
        # self.segEditorWidget.setMasterVolumeNode(masterVolumeNode)
        slicer.mrmlScene.RemoveNode(labelmapNode)

        # set segment names
        segmentation = self.segmentationNode.GetSegmentation()
        # print('DEBUG: range(segmentation.GetNumberOfSegments()) =', range(segmentation.GetNumberOfSegments()))
        segments = [segmentation.GetNthSegment(segInd) for segInd in range(segmentation.GetNumberOfSegments())]

        segmentLabelDict = {segNum: segment for segNum, segment in enumerate(segments)}
        print('DEBUG: segmentLabelDict =', segmentLabelDict)

        for labelVal, labelName in LABEL_NAMES.items():
            color = np.array(LABEL_COLORS[labelVal], float) / 255
            if labelVal in segmentLabelDict:
                try:
                    print('INFO: loading segment for label ', labelVal)
                    segment = segmentLabelDict[labelVal]
                    defaultSegName = segment.GetName()
                    labelName = LABEL_NAMES[int(defaultSegName)]
                    segment.SetColor(color)
                    segment.SetName(labelName)
                except (KeyError, ValueError):
                    print('ERROR: problem getting label name for segment named', defaultSegName)
                    continue
            else:  # label is missing from labelmap, create empty segment
                print('Adding empty segment for class', labelName)
                segmentation.AddEmptySegment('', labelName, color)

        # configure views
        view_names = ['Red', 'Yellow', 'Green']
        for vol_node, view_name in zip(self.volNodes, view_names):
            view = slicer.app.layoutManager().sliceWidget(view_name)
            view.sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(vol_node.GetID())
            view.sliceLogic().GetSliceCompositeNode().SetLinkedControl(True)
            view.mrmlSliceNode().RotateToVolumePlane(vol_node)
            view.sliceController().setSliceVisible(True)  # show in 3d view
                

    def saveActiveSegmentation(self):
        if self.active_label_fn:

            # restore original label values
            segmentation = self.segmentationNode.GetSegmentation()
            for segInd in range(segmentation.GetNumberOfSegments()):
                segment = segmentation.GetNthSegment(segInd)
                try:
                    labelVal = LABEL_NAME_TO_LABEL_VAL[segment.GetName()]
                    segment.SetName(str(labelVal))
                except KeyError:
                    print('ERROR: saving segment number '+str(segInd)+' failed because its name ("'+str(segment.GetName())+'") is not one of '+str(LABEL_NAME_TO_LABEL_VAL.keys()))
                    continue

            # Save to file
            print('Saving seg to', self.active_label_fn)
            visibleSegmentIds = vtk.vtkStringArray()
            self.segmentationNode.GetDisplayNode().GetVisibleSegmentIDs(visibleSegmentIds)
            labelmapNode = slicer.vtkMRMLLabelMapVolumeNode()
            slicer.mrmlScene.AddNode(labelmapNode)
            slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(self.segmentationNode, visibleSegmentIds, labelmapNode, self.volNodes[0])
            slicer.util.saveNode(labelmapNode, self.active_label_fn)
            slicer.mrmlScene.RemoveNode(labelmapNode)
            

    def cleanup(self):
        try:
            self.saveActiveSegmentation()
        except:
            pass
        try:
            slicer.mrmlScene.RemoveNode(self.segmentationNode)
            del self.segmentationNode
        except:
            pass
        slicer.mrmlScene.Clear(0)
        
