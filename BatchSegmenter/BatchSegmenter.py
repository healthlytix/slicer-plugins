import os
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
        self.parent.title = "Batch Segmentation" # TODO make this more human readable by adding spaces
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["Brian Keating (Healthlytix)"] # replace with "Firstname Lastname (Organization)"
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

        # Layout within the dummy collapsible button
        dataFormLayout = qt.QFormLayout(dataCollapsibleButton)

        # Text area for volume name
        self.volumeNameLineEdit = qt.QLineEdit()
        dataFormLayout.addRow(qt.QLabel('    Volume Name:'), self.volumeNameLineEdit)

        # Text area for label volume name
        self.labelNameLineEdit = qt.QLineEdit()
        dataFormLayout.addRow(qt.QLabel('Label Vol. Name:'), self.labelNameLineEdit)

        # Combobox to display selected folders
        self.dataCombobox = qt.QComboBox()
        self.dataCombobox.enabled = False
        dataFormLayout.addRow(qt.QLabel('    Active Volume:'), self.dataCombobox)

        # Select Directories Button
        self.selectDataButton = qt.QPushButton("Load Data")
        self.selectDataButton.toolTip = "Select data directories."
        self.selectDataButton.enabled = True
        dataFormLayout.addRow(self.selectDataButton)


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
        self.selectDataButton.connect('clicked(bool)', self.onSelectDataButton)
        self.dataCombobox.connect('currentIndexChanged(const QString&)', self.onComboboxChanged)

        # ### TEMP - for development ###
        self.volumeNameLineEdit.text = 'ctvol_reg.mgh'  
        self.labelNameLineEdit.text = 'ventr_mask_reg.mgh'
        self.logic.selectedImageDict = {'ctcopilot00065': ('/Users/brian/Desktop/datasets/lv_segmentation/manual_segs/ctcopilot00065/ctvol_reg.mgh', '/Users/brian/Desktop/datasets/lv_segmentation/manual_segs/ctcopilot00065/ventr_mask_reg.mgh')}
        self.dataCombobox.addItem('ctcopilot00065')
        self.dataCombobox.enabled = True
        self.segCollapsibleButton.collapsed = False

    # def saveData(self):
    #     slicer.modules.segmentations.logic().ExportSegmentsToLabelmapNode(seg, ids, labelmapVolumeNode, reference)
    #     slicer.util.saveNode(slicer.util.getNode('MR-head'), filename)

    def onComboboxChanged(self, text):
        # TODO: make sure previous data is saved!!!
        slicer.mrmlScene.Clear(0)
        try:
            volFilename, labelFilename = self.logic.selectedImageDict[text]
        except KeyError:
            print('Could not find %s among selected images' % text)
            return

        # TODO: if there's not labelFilename, create empty seg:
        # addedSegmentID = segmentationNode.GetSegmentation().AddEmptySegment('seg name')

        # create vol/label nodes
        slicer.util.loadVolume(volFilename)
        slicer.util.loadLabelVolume(labelFilename)
        labelmapNodeName = os.path.splitext(os.path.basename(labelFilename))[0]
        labelmapNode = slicer.util.getNode(labelmapNodeName)
        volNodeName = os.path.splitext(os.path.basename(volFilename))[0]
        volNode = slicer.util.getNode(volNodeName)

        # create segmentation node
        segmentationNode = slicer.vtkMRMLSegmentationNode()
        segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(volNode)
        slicer.mrmlScene.AddNode(segmentationNode)
        slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(labelmapNode, segmentationNode)
        slicer.mrmlScene.RemoveNode(labelmapNode)

        # add segmentation node to segmentation widget
        self.segEditorWidget.setEnabled(True)
        self.segEditorWidget.setMasterVolumeNode(volNode)
        self.segEditorWidget.setSegmentationNode(segmentationNode)
        segmentationNode.CreateClosedSurfaceRepresentation()
        self.segCollapsibleButton.collapsed = False
        

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

            # load names into combobox
            self.dataCombobox.clear()
            self.dataCombobox.addItems(list(folderDict.keys()))
            self.dataCombobox.enabled = True

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
        self.selectedImageDict = OrderedDict()
        for folder in candidateFolders:
            caseVolName = os.path.join(folder, volName)
            caseLabelName = os.path.join(folder, labelName)
            caseName = os.path.basename(folder)
            if os.path.exists(caseVolName) and os.path.exists(caseLabelName):
                self.selectedImageDict[caseName] = (caseVolName, caseLabelName)
        return self.selectedImageDict


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
