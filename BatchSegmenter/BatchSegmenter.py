import os
from glob import glob
import unittest
from collections import OrderedDict
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging


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

        # Text area for volume name
        self.imageNamesLineEdit = qt.QLineEdit()
        dataFormLayout.addRow(qt.QLabel('Image Names:'), self.imageNamesLineEdit)

        # Text area for label volume name
        self.labelNamesLineEdit = qt.QLineEdit()
        dataFormLayout.addRow(qt.QLabel('Label Names:'), self.labelNamesLineEdit)

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


        #### Segmentation Area ####

        self.segCollapsibleButton = ctk.ctkCollapsibleButton()
        self.segCollapsibleButton.text = 'Segmentation'
        self.segCollapsibleButton.collapsed = True
        self.layout.addWidget(self.segCollapsibleButton)

        # Layout within the dummy collapsible button
        segFormLayout = qt.QFormLayout(self.segCollapsibleButton)
        self.segEditorWidget = slicer.qMRMLSegmentEditorWidget()
        self.segEditorWidget.setMRMLScene(slicer.mrmlScene)
        self.segmentEditorNode = slicer.vtkMRMLSegmentEditorNode()
        slicer.mrmlScene.AddNode(self.segmentEditorNode)
        self.segEditorWidget.setMRMLSegmentEditorNode(self.segmentEditorNode)
        self.segEditorWidget.enabled = True
        self.segEditorWidget.setSwitchToSegmentationsButtonVisible(False)
        # self.segEditorWidget.setSegmentationNodeSelectorVisible(False)
        # self.segEditorWidget.setMasterVolumeNodeSelectorVisible(False)
        self.segEditorWidget.setReadOnly(False)
        segFormLayout.addRow(self.segEditorWidget)

        
        # Add vertical spacer
        self.layout.addStretch(1)

        
        ### connections ###
        self.imageNamesLineEdit.connect('editingFinished()', self.updateImageList)
        self.labelNamesLineEdit.connect('editingFinished()', self.updateImageList)
        self.previousImageButton.connect('clicked(bool)', self.previousImage)
        self.nextImageButton.connect('clicked(bool)', self.nextImage)
        self.imageComboBox.connect('currentIndexChanged(const QString&)', self.onComboboxChanged)


        ### Logic ###
        self.image_label_dict = OrderedDict()
        self.selected_image_ind = None
        self.active_label_fn = None
        
        ### TEMP - for development ###
        self.imageNamesLineEdit.text = '/Users/brian/apps/slicer-batch-segmentation/data/images/*.mgz'
        self.labelNamesLineEdit.text = '/Users/brian/apps/slicer-batch-segmentation/data/prostate_segs/*.mgz'
        self.updateImageList()
        
    
    def updateImageList(self):
        """Load matching image-label pairs into a dict, update widgets appropriately"""
        image_fn_pattern = self.imageNamesLineEdit.text
        image_fns = sorted(glob(self.imageNamesLineEdit.text))
        label_fn_pattern = self.imageNamesLineEdit.text
        label_fns = sorted(glob(self.labelNamesLineEdit.text))
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
        
        # add segmentation node to segmentation widget
        self.segEditorWidget.setEnabled(True)
        self.segEditorWidget.setMasterVolumeNode(self.volNode)
        self.segEditorWidget.setSegmentationNode(self.segmentationNode)
        self.segmentationNode.CreateClosedSurfaceRepresentation()
        self.segCollapsibleButton.collapsed = False
        visibleSegmentIds = vtk.vtkStringArray()
        self.segmentationNode.GetDisplayNode().GetVisibleSegmentIDs(visibleSegmentIds)
        self.segEditorWidget.setCurrentSegmentID(visibleSegmentIds.GetValue(0))
        self.segEditorWidget.updateWidgetFromMRML()
        

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
        