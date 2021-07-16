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
slicer.util.pip_install('pandas')
import pandas as pd


class CompareSegs(ScriptedLoadableModule):

    def __init__(self, parent):
        ScriptedLoadableModule.__init__(self, parent)
        self.parent.title = "Compare Segmentations"
        self.parent.categories = ["Segmentation"]
        self.parent.dependencies = []
        self.parent.contributors = ["Brian Keating (Cortechs.ai)"]
        self.parent.helpText = """"""
        self.parent.helpText += self.getDefaultModuleDocumentationLink()
        self.parent.acknowledgementText = """"""


class CompareSegsWidget(ScriptedLoadableModuleWidget):

    def setup(self):
        ScriptedLoadableModuleWidget.setup(self)
        
        # Read config
        config_fn = os.path.join(os.path.dirname(__file__), 'config.json')
        print('Loading CompareSegs config from ', config_fn)
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
        dataFormLayout.addRow('Cases:', self.selectDataButton)

        # Combobox to display selected folders
        self.caseComboBox = qt.QComboBox()
        self.caseComboBox.enabled = False
        dataFormLayout.addRow('Active Case:', self.caseComboBox)

        # Navigate images buttons
        navigateImagesLayout = qt.QHBoxLayout()
        self.previousImageButton = qt.QPushButton('Previous Case')
        self.previousImageButton.enabled = False
        navigateImagesLayout.addWidget(self.previousImageButton)

        self.nextImageButton = qt.QPushButton('Next Case')
        self.nextImageButton.enabled = False
        navigateImagesLayout.addWidget(self.nextImageButton)
        dataFormLayout.addRow(navigateImagesLayout)

        # Widget for selecting ROI
        dataFormLayout.addRow('', qt.QLabel(''))  # empty row, for spacing
        selectRoiLayout = qt.QHBoxLayout()
        self.roiButtonGroup = qt.QButtonGroup(dataFormLayout)
        for num, label_name in enumerate(self.labelNameToLabelVal):
            button = qt.QRadioButton(label_name)
            if num == 0:
                button.setChecked(True)
            self.roiButtonGroup.addButton(button)
            selectRoiLayout.addWidget(button)
        dataFormLayout.addRow('ROI:', selectRoiLayout)

        # Widget for selecting view orientations
        dataFormLayout.addRow('', qt.QLabel(''))  # empty row, for spacing
        selectViewLayout = qt.QHBoxLayout()
        self.viewButtonGroup = qt.QButtonGroup(dataFormLayout)
        axialButton = qt.QRadioButton('axial')
        axialButton.setChecked(True)
        self.viewButtonGroup.addButton(axialButton)
        selectViewLayout.addWidget(axialButton)
        sagittalButton = qt.QRadioButton('sagittal')
        self.viewButtonGroup.addButton(sagittalButton)
        selectViewLayout.addWidget(sagittalButton)
        coronalButton = qt.QRadioButton('coronal')
        self.viewButtonGroup.addButton(coronalButton)
        selectViewLayout.addWidget(coronalButton)
        dataFormLayout.addRow('Orientation:', selectViewLayout)

        # Combobox for red/green/yellow slice views
        dataFormLayout.addRow('', qt.QLabel(''))  # empty row, for spacing
        imageNames = list(self.config['imageFilenamePatterns'].keys())
        self.redViewCombobox = qt.QComboBox()
        self.redViewCombobox.addItems(imageNames)
        self.redViewCombobox.setCurrentIndex(0)
        dataFormLayout.addRow('Red View Image:', self.redViewCombobox)
        self.greenViewCombobox = qt.QComboBox()
        self.greenViewCombobox.addItems(imageNames)
        self.greenViewCombobox.setCurrentIndex(1)
        dataFormLayout.addRow('Green View Image:', self.greenViewCombobox)
        self.yellowViewCombobox = qt.QComboBox()
        self.yellowViewCombobox.addItems(imageNames)
        self.yellowViewCombobox.setCurrentIndex(2)
        dataFormLayout.addRow('Yellow View Image:', self.yellowViewCombobox)


        ## Add vertical spacer to keep widgets near top
        self.layout.addStretch(1)
        
        ### connections ###
        self.selectDataButton.clicked.connect(self.onSelectDataButtonPressed)
        self.previousImageButton.connect('clicked(bool)', self.previousImage)
        self.nextImageButton.connect('clicked(bool)', self.nextImage)
        self.caseComboBox.connect('currentIndexChanged(const QString&)', self.onCaseComboboxChanged)
        self.redViewCombobox.connect('currentIndexChanged(const QString&)', self.onRedViewComboboxChanged)
        self.greenViewCombobox.connect('currentIndexChanged(const QString&)', self.onGreenViewComboboxChanged)
        self.yellowViewCombobox.connect('currentIndexChanged(const QString&)', self.onYellowViewComboboxChanged)
        self.viewButtonGroup.buttonClicked.connect(self.onViewOrientationChanged)
        self.roiButtonGroup.buttonClicked.connect(self.onRoiChanged)

        ### Logic ###
        self.imagePathsDf = pd.DataFrame()
        self.segmentationNode = None
        self.volNodes = OrderedDict()
        self.segmentations = OrderedDict()
        self.selected_image_ind = None
        self.active_label_fn = None
        self.dataFolders = None
        
        # temp debug
        self.imagePathsDf = pd.read_csv('/Users/brian/apps/slicer-plugins/CompareSegs/image_paths.csv')
        self.imagePathsDf = self.imagePathsDf.set_index('case') 
        self.updateWidgets()


    def onRedViewComboboxChanged(self, volName):
        self.setSliceViewVolume('Red', volName, self.volNodes[volName])


    def onGreenViewComboboxChanged(self, volName):
        self.setSliceViewVolume('Green', volName, self.volNodes[volName])


    def onYellowViewComboboxChanged(self, volName):
        self.setSliceViewVolume('Yellow', volName, self.volNodes[volName])


    def onRoiChanged(self, button):
        selectedLabelVal = self.labelNameToLabelVal[button.text]
        print('Change ROI to '+button.text)
        print('Label number '+selectedLabelVal)
        

    def onViewOrientationChanged(self, button):
        
        # set orientations
        sliceNodes = slicer.util.getNodesByClass('vtkMRMLSliceNode')
        for sliceNode in sliceNodes:
            if button.text == 'axial':
                sliceNode.SetOrientationToAxial()
            elif button.text == 'sagittal':
                sliceNode.SetOrientationToSagittal()
            elif button.text == 'coronal':
                sliceNode.SetOrientationToCoronal()
            else:
                print('ERROR: unknown orientation', button.text)

        # rotate to volume plane
        for volNode, view_name in zip(self.volNodes.values(), ['Red', 'Yellow', 'Green']):
            view = slicer.app.layoutManager().sliceWidget(view_name)
            view.mrmlSliceNode().RotateToVolumePlane(volNode)
        

    def onSelectDataButtonPressed(self):
        file_dialog = qt.QFileDialog(None, 'Select Data Folders')
        file_dialog.setFileMode(qt.QFileDialog.DirectoryOnly)
        file_dialog.setOption(qt.QFileDialog.DontUseNativeDialog, True)
        file_dialog.setOption(qt.QFileDialog.ShowDirsOnly, True)
        file_view = file_dialog.findChild(qt.QListView, 'listView')
        # make it possible to select multiple directories
        if file_view:
            file_view.setSelectionMode(qt.QAbstractItemView.MultiSelection)
        f_tree_view = file_dialog.findChild(qt.QTreeView)
        if f_tree_view:
            f_tree_view.setSelectionMode(qt.QAbstractItemView.MultiSelection)
        if file_dialog.exec_():
            labeler_folders = file_dialog.selectedFiles()
            self.imagePathsDf = self.loadImagePathsDataFrame(labeler_folders)
            self.updateWidgets()


    def loadImagePathsDataFrame(self, labeler_folders):
        """Make a DataFrame: rows=cases, cols=ims, values=paths"""

        # Create a set of all case folders (underneath `labeler_folders`)
        labeler_names = [os.path.basename(d) for d in labeler_folders]
        case_names = set()
        for labeler_folder in labeler_folders:
            labeler_cases = [os.path.basename(d) for d in glob(os.path.join(labeler_folder, '*')) if os.path.isdir(d)]
            case_names.update(labeler_cases)

        # Load image and seg paths for each case
        all_paths = []
        for case_name in sorted(case_names):
            case_paths = OrderedDict()
            case_paths['case'] = case_name

            # images (from any labeler_folder)
            for im_name, im_pattern in self.config['imageFilenamePatterns'].items():
                for labeler_folder in labeler_folders:
                    case_im_pattern = os.path.join(labeler_folder, case_name, im_pattern)
                    matching_paths = glob(case_im_pattern)
                    if len(matching_paths) == 1:
                        case_paths[im_name] = matching_paths[0]
                        break
                    elif len(matching_paths) == 0:
                        print('No images like ', case_im_pattern)
                    else:
                        print('Multiple images match ', case_im_pattern)
            
            # segs (from every labeler_folder)
            for labeler_folder in labeler_folders:
                seg_pattern = os.path.join(labeler_folder, case_name, self.config['segFilenamePattern'])
                matching_paths = glob(seg_pattern)
                if len(matching_paths) == 1:
                    labeler_name = os.path.basename(labeler_folder)
                    col_name = labeler_name + '.seg'
                    case_paths[col_name] = matching_paths[0]
                elif len(matching_paths) == 0:
                    print('No images like ', seg_pattern)
                else:
                    print('Multiple images match ', seg_pattern)

            all_paths.append(case_paths)
            
        # put everything into a DataFrame
        df = pd.DataFrame(all_paths)
        df = df.set_index('case') 

        # drop any rows/cases that are missing MRIs
        im_names = self.config['imageFilenamePatterns'].keys()
        df[~df[im_names].isna().any(1)]
        seg_cols = [col for col in df.columns if col.endswith('seg')]
        print('Loaded '+str(len(df))+' cases from '+str(len(seg_cols))+' labelers')
        
        return df


    def updateWidgets(self):
        """Load selected valid case names into the widget"""

        # select data button
        if len(self.imagePathsDf) > 1:
            self.selectDataButton.setText(str(len(self.imagePathsDf))+' cases')
        elif len(self.image_label_dict) == 1:
            self.selectDataButton.setText(self.imagePathsDf.index[0])
        
        # case combobox
        self.caseComboBox.clear()
        if len(self.imagePathsDf) > 0:
            case_names = list(self.imagePathsDf.index)
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
        if self.selected_image_ind > len(self.imagePathsDf) - 1:
            self.selected_image_ind -= len(self.imagePathsDf)
        self.caseComboBox.setCurrentIndex(self.selected_image_ind)


    def previousImage(self):
        self.selected_image_ind -= 1
        if self.selected_image_ind < 0:
            self.selected_image_ind += len(self.imagePathsDf)
        self.caseComboBox.setCurrentIndex(self.selected_image_ind)


    def onCaseComboboxChanged(self, case_name):
        """Load a new case when the user selects from the cases combobox

        This is the main function for loading images from disk, configuring the views, and creating
        a segmentation with the correct display names/colors.

        Arg:
            case_name (str): the name of the case (which was derived from the directory name). Should be 
                a key in ``self.image_label_dict``

        Raises:
            ValueError: if the config is missing name/color for one of the integer labels in the 
                label file
        """
        
        if len(self.imagePathsDf) == 0:
            return

        try:
            self.selected_image_ind = self.imagePathsDf.index.get_loc(case_name)
        except KeyError:
            raise ValueError('Tried to load non-existent case '+case_name)

        # select the filenames for this case
        try:
            row_dict = self.imagePathsDf.to_dict('index')[case_name]
            im_fns_dict = {name: path for name, path in row_dict.items() if name in self.config['imageFilenamePatterns']}
            seg_fns_dict = {name.replace('.seg', ''): path for name, path in row_dict.items() if name.endswith('seg')}
        except KeyError:
            print('Could not find '+case_name+' among selected images')
            return

        # remove existing nodes (if any)
        self.clearNodes()

        # create vol nodes
        self.loadVolumesFromFiles(im_fns_dict)

        # create segmentation
        self.createSegmentationsFromFilenames(seg_fns_dict)

        # set the correct orientation
        sliceNodes = slicer.util.getNodesByClass('vtkMRMLSliceNode')
        selectedOrientation = self.viewButtonGroup.checkedButton().text
        for sliceNode in sliceNodes:
            if selectedOrientation == 'axial':
                sliceNode.SetOrientationToAxial()
            elif selectedOrientation == 'sagittal':
                sliceNode.SetOrientationToSagittal()
            elif selectedOrientation == 'coronal':
                sliceNode.SetOrientationToCoronal()

        # configure views
        volNames = [
            self.redViewCombobox.currentText,
            self.greenViewCombobox.currentText,
            self.yellowViewCombobox.currentText,
        ]
        for volName, color in zip(volNames, ['Red', 'Green', 'Yellow']):
            volNode = self.volNodes[volName]
            self.setSliceViewVolume(color, volName, volNode)
        

    def setSliceViewVolume(self, color, volName, volNode):
        """Show the given volume in the 'color' slice view"""
        view = slicer.app.layoutManager().sliceWidget(color)
        view.sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(volNode.GetID())
        view.sliceLogic().GetSliceCompositeNode().SetLinkedControl(True)
        view.mrmlSliceNode().RotateToVolumePlane(volNode)
        view.sliceController().setSliceVisible(True)  # show in 3d view
        

    def loadVolumesFromFiles(self, filename_dict):
        self.volNodes = OrderedDict()
        for display_name, filename in filename_dict.items():
            volNode = slicer.util.loadVolume(filename)
            if volNode:
                volNode.GetScalarVolumeDisplayNode().SetInterpolate(0)
                self.volNodes[display_name] = volNode
            else:
                print('WARNING: Failed to load volume ', filename)
        if len(self.volNodes) == 0:
            print('Failed to load any volumes ({filenames})!')
            return


    def createSegmentationsFromFilenames(self, seg_fns_dict):
        print('INFO: CompareSegs.createSegmentationFromFile invoked', seg_fns_dict)

        # create segs
        self.segmentations = {}
        for labeler_name, seg_fn in seg_fns_dict.items():

            # create labelmap
            if not seg_fn:
                continue
            labelmapNode = slicer.util.loadLabelVolume(seg_fn)
            node_name = os.path.basename(seg_fn).split('.')[0]+'_'+labeler_name
            labelmapNode.SetName(node_name)
            if not labelmapNode:
                print('Failed to load label volume ', seg_fn)
                continue

            # create segmentation node from labelVolume
            segmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode', labeler_name+' segmentation')
            segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(list(self.volNodes.values())[0])
            # segmentationNode.CreateClosedSurfaceRepresentation()
            segmentationNode.CreateDefaultDisplayNodes()
            slicer.mrmlScene.AddNode(segmentationNode)
            slicer.vtkSlicerSegmentationsModuleLogic.ImportLabelmapToSegmentationNode(labelmapNode, segmentationNode)
            slicer.mrmlScene.RemoveNode(labelmapNode)

            self.segmentations[labeler_name] = segmentationNode


    def clearNodes(self):
        print('INFO: CompareSegs.clearNodes invoked')
        for volNode in self.volNodes.values():
            slicer.mrmlScene.RemoveNode(volNode)
        for segmentationNode in self.segmentations.values():
            if segmentationNode:
                slicer.mrmlScene.RemoveNode(segmentationNode)
        self.volNodes = OrderedDict()

                
    def cleanup(self):
        print('INFO: CompareSegs.cleanup() invoked')
        self.clearNodes()


def loadLabelArrayFromFile(labelFilename):
    """Load raw numpy array from a label image file"""
    labelmapNode = slicer.util.loadLabelVolume(labelFilename)
    labelArray = slicer.util.arrayFromVolume(labelmapNode)
    slicer.mrmlScene.RemoveNode(labelmapNode)
    return labelArray
