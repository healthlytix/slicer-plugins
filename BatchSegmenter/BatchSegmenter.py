import os
import json
from glob import glob
import tempfile
import traceback
from collections import OrderedDict
import numpy as np
import vtk, qt, ctk, slicer
from slicer.ScriptedLoadableModule import *
import logging


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


"""
Possibly relevant example: https://github.com/Slicer/Slicer/blob/a18612bb2584018822347ff4db16439b5c578e00/Utilities/Templates/Modules/Scripted/TemplateKey.py#L104-L108
Use VTKObservationMixin and removeObservers()
"""
class BatchSegmenterWidget(ScriptedLoadableModuleWidget):

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        
        # Read config
        config_fn = os.path.join(os.path.dirname(__file__), 'batch-segmenter-config.json')
        print('Loading config from ', config_fn)
        with open(config_fn) as f:
            self.config = json.load(f)
        self.labelNameToLabelVal = {val: key for key, val in self.config['labelNames'].items()}

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
        dataFormLayout.addRow(qt.QLabel('Cases:'), self.selectDataButton)

        # Combobox to display selected folders
        self.caseComboBox = qt.QComboBox()
        self.caseComboBox.enabled = False
        dataFormLayout.addRow(qt.QLabel('Active Case:'), self.caseComboBox)

        # Navigate images buttons
        navigateImagesLayout = qt.QHBoxLayout()
        self.previousImageButton = qt.QPushButton('Previous Case')
        self.previousImageButton.enabled = False
        navigateImagesLayout.addWidget(self.previousImageButton)

        self.nextImageButton = qt.QPushButton('Next Case')
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
        self.segmentationNode = None
        self.volNodes = []
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
                folder_ims = [glob(os.path.join(data_folder, im_fn)) for im_fn in self.config['imageFilenamePatterns']]
                has_required_ims = all(len(ims)==1 for ims in folder_ims)
                has_label = len(glob(os.path.join(data_folder, self.config['labelFilenamePattern']))) == 1
                if has_required_ims and has_label:
                    folder_name = os.path.basename(data_folder)
                    im_fns = [ims[0] for ims in folder_ims]
                    label_fn = glob(os.path.join(data_folder, self.config['labelFilenamePattern']))[0]
                    self.image_label_dict[folder_name] = im_fns, label_fn
                else:
                    print('WARNING: Skipping '+data_folder+' because it is missing (or contains multiple) required input images')
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
        """Load a new case when the user selects from the cases combobox

        This is the main function for loading images from disk, configuring the views, and creating
        a segmentation with the correct display names/colors.

        Arg:
            text (str): the name of the case (which was derived from the directory name). Should be 
                a key in ``self.image_label_dict``

        Raises:
            ValueError: if the config is missing name/color for one of the integer labels in the 
                label file
        """
        
        if not self.image_label_dict:
            return

        # save old seg before loading the new one
        if self.segmentationNode:
            self.saveActiveSegmentation()

        try:
            self.selected_image_ind = list(self.image_label_dict.keys()).index(text)
        except ValueError:
            return

        # select the filenames for this case
        try:
            im_fns, label_fn = self.image_label_dict[text]
        except KeyError:
            print('Could not find %s among selected images' % text)
            return
        self.active_label_fn = label_fn

        # remove existing nodes (if any)
        self.clearNodes()
        
        # TODO: if there's not label_fn, create empty seg

        # make all slice views axial before loading volumes
        sliceNodes = slicer.util.getNodesByClass('vtkMRMLSliceNode')
        for sliceNode in sliceNodes:
            sliceNode.SetOrientationToAxial()
        
        # create vol nodes
        self.loadVolumesFromFiles(im_fns)

        # create segmentation
        self.createSegmentationFromFile(label_fn)

        # configure views
        for volNode, view_name in zip(self.volNodes, ['Red', 'Yellow', 'Green']):
            view = slicer.app.layoutManager().sliceWidget(view_name)
            view.sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(volNode.GetID())
            view.sliceLogic().GetSliceCompositeNode().SetLinkedControl(True)
            view.mrmlSliceNode().RotateToVolumePlane(volNode)
            view.sliceController().setSliceVisible(True)  # show in 3d view
                
    def loadVolumesFromFiles(self, filenames):
        self.volNodes = []
        for im_fn in filenames:
            volNode = slicer.util.loadVolume(im_fn)
            if volNode:
                volNode.GetScalarVolumeDisplayNode().SetInterpolate(0)
                self.volNodes.append(volNode)
            else:
                print('WARNING: Failed to load volume ', im_fn)
        if len(self.volNodes) == 0:
            print('Failed to load any volumes from folder '+text+'!')
            return


    def createSegmentationFromFile(self, label_fn):
        print('INFO: BatchSegmenter.createSegmentationFromFile invoked', label_fn)

        # create label node as a labelVolume
        labelmapNode = slicer.util.loadLabelVolume(label_fn)
        if not labelmapNode:
            print('Failed to load label volume ', label_fn)
            return

        # create segmentation node from labelVolume
        self.segmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode', 'Tumor Segmentation')
        self.segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(self.volNodes[0])
        self.segmentationNode.CreateDefaultDisplayNodes()
        slicer.mrmlScene.AddNode(self.segmentationNode)
        slicer.vtkSlicerSegmentationsModuleLogic.ImportLabelmapToSegmentationNode(labelmapNode, self.segmentationNode)
        self.segEditorWidget.setSegmentationNode(self.segmentationNode)
        slicer.mrmlScene.RemoveNode(labelmapNode)

        # figure out segment labels
        segmentation = self.segmentationNode.GetSegmentation()
        integerLabels = np.unique(slicer.util.arrayFromVolume(labelmapNode))
        integerLabels = np.delete(integerLabels, np.argwhere(integerLabels==0))  # remove background label
        segments = [segmentation.GetNthSegment(segInd) for segInd in range(segmentation.GetNumberOfSegments())]
        labelToSegment = {str(label): segment for label, segment in zip(integerLabels, segments)}
        
        # verify that labels in label_fn match those in the config
        existingLabelsAreInConfig = [label in self.config['labelNames'] for label in labelToSegment]
        if not all(existingLabelsAreInConfig):
            raise ValueError('Some of the integer labels in '+label_fn+' ('+str(labelToSegment.keys())+') '+' are missing from config ('+str(self.config['labelNames'].keys())+')')

        # set colors and names for segments
        for labelVal, labelName in self.config['labelNames'].items():
            color = np.array(self.config['labelColors'][labelVal], float) / 255
            if labelVal in labelToSegment:
                try:
                    segment = labelToSegment[labelVal]
                    labelName = self.config['labelNames'][labelVal]
                    segment.SetColor(color)
                    segment.SetName(labelName)
                    print('INFO: Adding segment for label ', labelVal, ' as ', labelName)
                except KeyError:
                    print('ERROR: problem getting label name or color for segment ', labelVal)
                    continue
            else:  # label is missing from labelmap, create empty segment
                print('INFO: Adding empty segment for class', labelName)
                segmentation.AddEmptySegment(str(labelVal), labelName, color)
                

    def saveActiveSegmentation(self):
        if self.active_label_fn:
            print('INFO: BatchSegmenter.saveActiveSegmentation() invoked', self.active_label_fn)

            # restore original label values
            segmentation = self.segmentationNode.GetSegmentation()
            for segInd in range(segmentation.GetNumberOfSegments()):
                segment = segmentation.GetNthSegment(segInd)
                try:
                    labelVal = self.labelNameToLabelVal[segment.GetName()]
                    print('INFO: saving '+segment.GetName()+' segment as '+str(labelVal))
                    segment.SetName(str(labelVal))
                except KeyError:
                    # TODO: create user-visible error here (an alert box or something)
                    print('ERROR: saving segment number '+str(segInd)+' failed because its name ("'+str(segment.GetName())+'") is not one of '+str(self.labelNameToLabelVal.keys()))
                    return

            # Save to file
            if self.segmentationNode and self.segmentationNode.GetDisplayNode():
                print('Saving seg to', self.active_label_fn)

                # make a list of segment IDs *that are always ordered correctly*
                visibleSegmentIds = vtk.vtkStringArray()
                for labelVal in self.config['labelNames']:  # assumes that the config list of labelNames is in order
                    visibleSegmentIds.InsertNextValue(labelVal)
                visibleSegmentIdsList = [visibleSegmentIds.GetValue(ind) for ind in range(visibleSegmentIds.GetNumberOfValues())]
                
                labelmapNode = slicer.vtkMRMLLabelMapVolumeNode()
                slicer.mrmlScene.AddNode(labelmapNode)
                slicer.vtkSlicerSegmentationsModuleLogic.ExportSegmentsToLabelmapNode(self.segmentationNode, visibleSegmentIds, labelmapNode, self.volNodes[0])
                slicer.util.saveNode(labelmapNode, self.active_label_fn)
                slicer.mrmlScene.RemoveNode(labelmapNode)
                        

    def clearNodes(self):
        print('INFO: BatchSegmenter.clearNodes invoked')
        for volNode in self.volNodes:
            slicer.mrmlScene.RemoveNode(volNode)
        if self.segmentationNode:
            slicer.mrmlScene.RemoveNode(self.segmentationNode)
        self.segmentationNode = None
        self.volNodes = []

                
    def cleanup(self):
        print('INFO: BatchSegmenter.cleanup() invoked')
        if self.segmentationNode:
            self.saveActiveSegmentation()
        self.clearNodes()


def loadLabelArrayFromFile(labelFilename):
    """Load raw numpy array from a label image file"""
    labelmapNode = slicer.util.loadLabelVolume(labelFilename)
    labelArray = slicer.util.arrayFromVolume(labelmapNode)
    slicer.mrmlScene.RemoveNode(labelmapNode)
    return labelArray


class BatchSegmenterTest():

    def delayDisplay(self, message, msec=150):
        """Display a small dialog and wait
    
        This does two things: 1) it lets the event loop catch up
        to the state of the test so that rendering and widget updates
        have all taken place before the test continues and 2) it
        shows the user/developer/tester the state of the test
        so that we'll know when it breaks
        """
        print('TEST:', message)
        self.info = qt.QDialog()
        self.infoLayout = qt.QVBoxLayout()
        self.info.setLayout(self.infoLayout)
        self.label = qt.QLabel(message,self.info)
        self.infoLayout.addWidget(self.label)
        qt.QTimer.singleShot(msec, self.info.close)
        self.info.exec_()


    def setUp(self):
        """ Do whatever is needed to reset the state - typically a scene clear will be enough."""
        slicer.mrmlScene.Clear(0)


    def runTest(self):
        """Run as few or as many tests as needed here."""
        self.setUp()
        self.testBatchSegmenter()


    def testBatchSegmenter(self):
        self.delayDisplay('BatchSegmenter tests')

        self.delayDisplay('Creating BatchSegmenter widgets')
        
        mainWindow = slicer.util.mainWindow()
        mainWindow.moduleSelector().selectModule('BatchSegmenter')
        batchSegmentationWidget = slicer.modules.BatchSegmenterWidget

        testDataDir = os.path.join(os.path.dirname(__file__), 'Data')
        sampleVolFilenames = [
            os.path.join(testDataDir, 'T1-postcontrast.nii'),
            os.path.join(testDataDir, 'T2.nii'),
            os.path.join(testDataDir, 'FLAIR.nii'),
            os.path.join(testDataDir, 'T1-precontrast.nii')
        ]
        tempdir = tempfile.mkdtemp()

        # test round-trip with all segments
        sampleLabelFilename = os.path.join(testDataDir, 'tumor-seg.nii')
        originalSeg = loadLabelArrayFromFile(sampleLabelFilename)
        batchSegmentationWidget.loadVolumesFromFiles(sampleVolFilenames)
        batchSegmentationWidget.createSegmentationFromFile(sampleLabelFilename)
        testSegFilename = os.path.join(tempdir, 'tumor-seg-test.nii')
        batchSegmentationWidget.active_label_fn = testSegFilename
        batchSegmentationWidget.saveActiveSegmentation()
        finalSeg = loadLabelArrayFromFile(testSegFilename)
        try:
            np.testing.assert_array_equal(originalSeg, finalSeg)
            self.delayDisplay('Round trip segmentation read-write-read test 1 successful')
        except AssertionError as e:
            self.delayDisplay('Round trip segmentation read-write-read test 1 FAILED')
            raise e

        batchSegmentationWidget.clearNodes()

        # test round-trip with segments labeled 1, 3 (no edema/label 2 ROI)
        sampleLabelFilename = os.path.join(testDataDir, 'tumor-seg-missing-edema.nii')
        originalSeg = loadLabelArrayFromFile(sampleLabelFilename)
        batchSegmentationWidget.loadVolumesFromFiles(sampleVolFilenames)
        batchSegmentationWidget.createSegmentationFromFile(sampleLabelFilename)
        testSegFilename = os.path.join(tempdir, 'tumor-seg-test.nii')
        batchSegmentationWidget.active_label_fn = testSegFilename
        batchSegmentationWidget.saveActiveSegmentation()
        finalSeg = loadLabelArrayFromFile(testSegFilename)
        try:
            np.testing.assert_array_equal(originalSeg, finalSeg)
            self.delayDisplay('Round trip segmentation read-write-read test 2 successful')
        except AssertionError as e:
            self.delayDisplay('Round trip segmentation read-write-read test 2 FAILED')
            raise e

        batchSegmentationWidget.clearNodes()
        
        self.delayDisplay('Tests passed!')
    