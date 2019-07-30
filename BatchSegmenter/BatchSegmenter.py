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
        self.logic = BatchSegmenterLogic()


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
        self.segmentEditorNode = slicer.mrmlScene.AddNewNodeByClass("vtkMRMLSegmentEditorNode")
        self.segEditorWidget.setMRMLSegmentEditorNode(self.segmentEditorNode)
        self.segEditorWidget.enabled = True
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
        
        # # ### TEMP - for development ###
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
        if self.image_label_dict:
            self.imageComboBox.addItems(list(self.image_label_dict.keys()))  # load names into combobox
            self.imageComboBox.enabled = True
            self.nextImageButton.enabled = True
            self.previousImageButton.enabled = True
            self.selected_image_ind = 0
        else:
            self.imageComboBox.enabled = False
            self.nextImageButton.enabled = False
            self.previousImageButton.enabled = False
            self.selected_image_ind = None

    
    def nextImage(self):
        self.selected_image_ind += 1
        if self.selected_image_ind > len(self.image_label_dict) - 1:
            self.selected_image_ind -= len(self.image_label_dict)
        self.updateSelectedImage()


    def previousImage(self):
        self.selected_image_ind -= 1
        if self.selected_image_ind < 0:
            self.selected_image_ind += len(self.image_label_dict)
        self.updateSelectedImage()


    def onComboboxChanged(self, text):
        self.selected_image_ind = list(self.image_label_dict.keys()).index(text)

    
    def updateSelectedImage(self):
        self.imageComboBox.setCurrentIndex(self.selected_image_ind)


    

    # def onComboboxChanged(self, text):
    #     # TODO: make sure previous data is saved!!!
    #     slicer.mrmlScene.Clear(0)
    #     try:
    #         volFilename, labelFilename = self.logic.imageDict[text]
    #     except KeyError:
    #         print('Could not find %s among selected images' % text)
    #         return

    #     # TODO: if there's not labelFilename, create empty seg:
    #     # addedSegmentID = segmentationNode.GetSegmentation().AddEmptySegment('seg name')

    #     aSegmentationIsLoaded = hasattr(self, 'segmentationNode')
    #     if aSegmentationIsLoaded and self.autosaveCheckbox.isChecked():
    #         self.onSaveSegButtonPressed()
        
    #     # create vol/label nodes
    #     [success, self.volNode] = slicer.util.loadVolume(volFilename, returnNode=True)
    #     if not success:
    #         print('Failed to load volume ', volFilename)
    #         return
    #     [success, self.labelmapNode] = slicer.util.loadLabelVolume(labelFilename, returnNode=True)
    #     if success:
    #         self.labelFilename = labelFilename
    #     else:
    #         print('Failed to load label volume ', labelFilename)
    #         return
        
    #     # set window level
    #     # TODO: let user set it manually, then copy windowing when volume is changed
    #     displayNode = self.volNode.GetDisplayNode()
    #     displayNode.AutoWindowLevelOff()
    #     displayNode.SetLevel(40)
    #     displayNode.SetWindow(80)
        
    #     # create segmentation node
    #     self.segmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode', 'segmentationNode')
    #     self.segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(self.volNode)
    #     self.segmentationNode.CreateDefaultDisplayNodes()
    #     slicer.mrmlScene.AddNode(self.segmentationNode)
    #     slicer.vtkSlicerSegmentationsModuleLogic.ImportLabelmapToSegmentationNode(self.labelmapNode, self.segmentationNode)
    #     # slicer.mrmlScene.RemoveNode(labelmapNode)
        
    #     # add segmentation node to segmentation widget
    #     self.segEditorWidget.setEnabled(True)
    #     self.segEditorWidget.setSegmentationNode(self.segmentationNode)
    #     self.segEditorWidget.setMasterVolumeNode(self.volNode)
    #     self.segmentationNode.CreateClosedSurfaceRepresentation()
    #     # self.segCollapsibleButton.collapsed = False

    #     if ~self.autosaveCheckbox.isChecked():
    #         self.saveSegButton.enabled = True


    def onSelectDataButton(self):
        file_dialog = qt.QFileDialog()
        file_dialog.setFileMode(qt.QFileDialog.DirectoryOnly)
        file_dialog.setOption(qt.QFileDialog.DontUseNativeDialog, True)
        file_view = file_dialog.findChild(qt.QListView, 'listView')

        # to make it possible to select multiple directories:
        if file_view:
            file_view.setSelectionMode(qt.QAbstractItemView.MultiSelection)
        f_tree_view = file_dialog.findChild(qt.QTreeView)
        if f_tree_view:
            f_tree_view.setSelectionMode(qt.QAbstractItemView.MultiSelection)

        if file_dialog.exec_():
            # get folders from dialog
            candidateFolders = file_dialog.selectedFiles()

            # keep folders that have the correct volumes in them
            volName = self.volumeNameLineEdit.text
            labelName = self.labelNameLineEdit.text
            folderDict = self.logic.selectValidFolders(candidateFolders, volName, labelName)

            

    def cleanup(self):
        pass
        


class BatchSegmenterLogic(ScriptedLoadableModuleLogic):
    """This class should implement all the actual
    computation done by your module.  The interface
    should be such that other python code can import
    this class and make use of the functionality without
    requiring an instance of the Widget.
    """

    def selectValidFolders(self, candidateFolders, volName, labelName):
        candidateFolders = sorted(candidateFolders, key=lambda f: os.path.basename(f))
        self.volName = volName
        self.labelName = labelName
        self.imageDict = OrderedDict()
        if not self.volName or not self.labelName:
            print('Error: you should specify vol/label vol filenames')
            return
        for folder in candidateFolders:
            caseVolName = os.path.join(folder, volName)
            caseLabelName = os.path.join(folder, labelName)
            caseName = os.path.basename(folder)
            if os.path.exists(caseVolName) and os.path.exists(caseLabelName):
                self.imageDict[caseName] = (caseVolName, caseLabelName)
        return self.imageDict


    def hasImageData(self,volumeNode):
        """This is an example logic method that
        returns true if the passed in volume
        node has valid image data
        """
        if not volumeNode:
            logging.debug('hasImageData failed: no volume node')
            return False
        if volumeNode.GetImageData() is None:
            logging.debug('hasImageData failed: no image data in volume node')
            return False
        return True

    def isValidInputOutputData(self, inputVolumeNode, outputVolumeNode):
        """Validates if the output is not the same as input"""
        if not inputVolumeNode:
            logging.debug('isValidInputOutputData failed: no input volume node defined')
            return False
        if not outputVolumeNode:
            logging.debug('isValidInputOutputData failed: no output volume node defined')
            return False
        if inputVolumeNode.GetID()==outputVolumeNode.GetID():
            logging.debug('isValidInputOutputData failed: input and output volume is the same. Create a new volume for output to avoid this error.')
            return False
        return True


# class BatchSegmenterTest(ScriptedLoadableModuleTest):
#     """
#     This is the test case for your scripted module.
#     Uses ScriptedLoadableModuleTest base class, available at:
#     https://github.com/Slicer/Slicer/blob/master/Base/Python/slicer/ScriptedLoadableModule.py
#     """

#     def setUp(self):
#         """ Do whatever is needed to reset the state - typically a scene clear will be enough.
#         """
#         slicer.mrmlScene.Clear(0)

#     def runTest(self):
#         """Run as few or as many tests as needed here.
#         """
#         self.setUp()
#         self.test_BatchSegmenter1()

#     def test_BatchSegmenter1(self):
#         """ Ideally you should have several levels of tests.  At the lowest level
#         tests should exercise the functionality of the logic with different inputs
#         (both valid and invalid).  At higher levels your tests should emulate the
#         way the user would interact with your code and confirm that it still works
#         the way you intended.
#         One of the most important features of the tests is that it should alert other
#         developers when their changes will have an impact on the behavior of your
#         module.  For example, if a developer removes a feature that you depend on,
#         your test should break so they know that the feature is needed.
#         """

#         self.delayDisplay("Starting the test")
#         #
#         # first, get some data
#         #
#         import SampleData
#         SampleData.downloadFromURL(
#         nodeNames='FA',
#         fileNames='FA.nrrd',
#         uris='http://slicer.kitware.com/midas3/download?items=5767')
#         self.delayDisplay('Finished with download and loading')

#         volumeNode = slicer.util.getNode(pattern="FA")
#         logic = BatchSegmenterLogic()
#         self.assertIsNotNone( logic.hasImageData(volumeNode) )
#         self.delayDisplay('Test passed!')
