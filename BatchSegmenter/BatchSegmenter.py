import os
from glob import glob
import unittest
from collections import OrderedDict
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging


IMAGE_PATTERNS = [
    'BraTS20_Training_???_t1ce.nii.gz',
    'BraTS20_Training_???_t2.nii.gz',
    'BraTS20_Training_???_flair.nii.gz',
    'BraTS20_Training_???_t1.nii.gz'
]
LABEL_PATTERN = 'BraTS20_Training_???_seg.nii.gz'


class BatchSegmenter(ScriptedLoadableModule):
    """Uses ScriptedLoadableModule base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Batch Segmentation Editor"
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["Brian Keating (Healthlytix)"]
        self.parent.helpText = """"""
        self.parent.helpText += self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = """"""


class BatchSegmenterWidget(ScriptedLoadableModuleWidget):
    """Uses ScriptedLoadableModuleWidget base class, available at:
    https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
    """

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
        self.imageComboBox = qt.QComboBox()
        self.imageComboBox.enabled = False
        dataFormLayout.addRow(qt.QLabel('Active Volume:'), self.imageComboBox)

        # Navigate images buttons
        navigateImagesLayout = qt.QHBoxLayout()
        self.previousImageButton = qt.QPushButton('Previous Image')
        self.previousImageButton.enabled = False
        navigateImagesLayout.addWidget(self.previousImageButton)

        self.nextImageButton = qt.QPushButton('Next Image')
        self.nextImageButton.enabled = False
        navigateImagesLayout.addWidget(self.nextImageButton)
        dataFormLayout.addRow(navigateImagesLayout)

        # Add vertical spacer to keep widgets near top
        self.layout.addStretch(1)
        
        ### connections ###
        self.selectDataButton.clicked.connect(self.onSelectDataButtonPressed)
        self.previousImageButton.connect('clicked(bool)', self.previousImage)
        self.nextImageButton.connect('clicked(bool)', self.nextImage)
        self.imageComboBox.connect('currentIndexChanged(const QString&)', self.onComboboxChanged)

        ### Logic ###
        self.image_label_dict = OrderedDict()
        self.selected_image_ind = None
        self.active_label_fn = None
        self.dataFolders = None
        
        
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
            if len(self.image_label_dict) > 1:
                self.selectDataButton.setText(str(len(self.image_label_dict))+' cases')
            elif len(self.image_label_dict) == 1:
                self.selectDataButton.setText(os.path.basename(self.image_label_dict.keys()[0]))

            # self.updateImageList()


    def updateImageList(self):
        """Load matching image-label pairs into a dict, update widgets appropriately"""
        if not self.image_label_dict:
            return
        
        image_fns = glob(os.path.join(self.dataFolder, '*'))
        label_fns = sorted(glob(os.path.join(self.labelFolder, '*')))
        label_dict = {os.path.splitext(os.path.basename(fn))[0]: fn for fn in label_fns}
        self.image_label_dict = OrderedDict()
        for image_fn in image_fns:
            case_name = os.path.splitext(os.path.basename(image_fn))[0]
            if case_name in label_dict:
                label_fn = label_dict[case_name]
                self.image_label_dict[case_name] = image_fn, label_fn

        self.imageComboBox.clear()
        self.active_label_fn = None
        if self.image_label_dict:
            case_names = list(self.image_label_dict.keys())
            self.imageComboBox.addItems(case_names)  # load names into combobox
            self.imageComboBox.enabled = True
            self.nextImageButton.enabled = True
            self.previousImageButton.enabled = True
            self.selected_image_ind = 0
            self.active_label_fn = self.image_label_dict[case_names[0]][1]
        else:
            self.imageComboBox.enabled = False
            self.nextImageButton.enabled = False
            self.previousImageButton.enabled = False
            self.selected_image_ind = None
            self.active_label_fn = None

    
    def nextImage(self):
        self.selected_image_ind += 1
        if self.selected_image_ind > len(self.image_label_dict) - 1:
            self.selected_image_ind -= len(self.image_label_dict)
        self.imageComboBox.setCurrentIndex(self.selected_image_ind)


    def previousImage(self):
        self.selected_image_ind -= 1
        if self.selected_image_ind < 0:
            self.selected_image_ind += len(self.image_label_dict)
        self.imageComboBox.setCurrentIndex(self.selected_image_ind)


    def onComboboxChanged(self, text):
        
        if not self.image_label_dict:
            return

        # save old seg before loading the new one
        self.saveActiveSegmentation()
        try:
            self.selected_image_ind = list(self.image_label_dict.keys()).index(text)
        except ValueError:
            return

        slicer.mrmlScene.Clear(0)
        try:
            volFilename, labelFilename = self.image_label_dict[text]
        except KeyError:
            print('Could not find %s among selected images' % text)
            return
        self.active_label_fn = labelFilename


        # TODO: if there's not labelFilename, create empty seg:
        # addedSegmentID = segmentationNode.GetSegmentation().AddEmptySegment('seg name')
        

        # create vol/label nodes
        [success, self.volNode] = slicer.util.loadVolume(volFilename, returnNode=True)
        if not success:
            print('Failed to load volume ', volFilename)
            return
        [success, labelmapNode] = slicer.util.loadLabelVolume(labelFilename, returnNode=True)
        if not success:
            print('Failed to load label volume ', labelFilename)
            return
                
        # create segmentation node
        try:
            slicer.mrmlScene.RemoveNode(self.segmentationNode)
            del self.segmentationNode
        except:
            pass
        self.segmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode', 'Prostate Segmentation')
        self.segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(self.volNode)
        self.segmentationNode.CreateDefaultDisplayNodes()
        slicer.mrmlScene.AddNode(self.segmentationNode)
        slicer.vtkSlicerSegmentationsModuleLogic.ImportLabelmapToSegmentationNode(labelmapNode, self.segmentationNode)
        slicer.mrmlScene.RemoveNode(labelmapNode)
        

    def saveActiveSegmentation(self):
        if self.active_label_fn:
            print('Saving seg to', self.active_label_fn)
            visibleSegmentIds = vtk.vtkStringArray()
            self.segmentationNode.GetDisplayNode().GetVisibleSegmentIDs(visibleSegmentIds)
            labelmapNode = slicer.vtkMRMLLabelMapVolumeNode()
            slicer.mrmlScene.AddNode(labelmapNode)
            slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(self.segmentationNode, visibleSegmentIds, labelmapNode, self.volNode)
            slicer.util.saveNode(labelmapNode, self.active_label_fn)
            

    def cleanup(self):
        pass
        