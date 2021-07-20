import os
import json
from glob import glob
import tempfile
import traceback
from collections import OrderedDict
import numpy as np
import vtk, qt, ctk, slicer
import SimpleITK as sitk
import sitkUtils
from slicer.ScriptedLoadableModule import *
import logging
slicer.util.pip_install('pandas')
import pandas as pd


def numpy_to_sitk_image(numpy_arr, reference_im=None):
    sitk_im = sitk.GetImageFromArray(numpy_arr)
    if reference_im:
        sitk_im.SetOrigin(tuple(reference_im.GetOrigin()))
        sitk_im.SetSpacing(tuple(reference_im.GetSpacing()))
        sitk_im.SetDirection(reference_im.GetDirection())
    return sitk_im


def GetSlicerITKReadWriteAddress(nodeObjectOrName):
    """ This function will return the ITK FileIO formatted text address
            so that the image can be read directly from the MRML scene
    """
    myNode = nodeObjectOrName if isinstance(nodeObjectOrName, slicer.vtkMRMLNode) else slicer.util.getNode(nodeObjectOrName)
    myNodeSceneAddress = myNode.GetScene().GetAddressAsString("").replace('Addr=','')
    myNodeSceneID = myNode.GetID()
    myNodeFullITKAddress = 'slicer:' + myNodeSceneAddress + '#' + myNodeSceneID
    return myNodeFullITKAddress


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
        self.labelNameToLabelVal = {val: int(key) for key, val in self.config['labelNames'].items()}

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
        self.previousCaseButton = qt.QPushButton('Previous Case')
        self.previousCaseButton.enabled = False
        navigateImagesLayout.addWidget(self.previousCaseButton)

        self.nextCaseButton = qt.QPushButton('Next Case')
        self.nextCaseButton.enabled = False
        navigateImagesLayout.addWidget(self.nextCaseButton)
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
        self.selectedLabelVal = list(self.labelNameToLabelVal.values())[0]
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
        self.previousCaseButton.connect('clicked(bool)', self.previousCase)
        self.nextCaseButton.connect('clicked(bool)', self.nextCase)
        self.caseComboBox.connect('currentIndexChanged(const QString&)', self.onCaseComboboxChanged)
        self.redViewCombobox.connect('currentIndexChanged(const QString&)', self.onRedViewComboboxChanged)
        self.greenViewCombobox.connect('currentIndexChanged(const QString&)', self.onGreenViewComboboxChanged)
        self.yellowViewCombobox.connect('currentIndexChanged(const QString&)', self.onYellowViewComboboxChanged)
        self.viewButtonGroup.buttonClicked.connect(self.onViewOrientationChanged)
        self.roiButtonGroup.buttonClicked.connect(self.onRoiChanged)

        ### Logic ###
        self.imagePathsDf = pd.DataFrame()
        self.volNodes = OrderedDict()
        self.selected_image_ind = None
        self.active_label_fn = None
        self.dataFolders = None
        self.seg_fns_dict = {}
        
        # TEMP DEBUG
        self.imagePathsDf = pd.read_csv('/Users/brian/apps/slicer-plugins/CompareSegs/image_paths.csv')
        self.imagePathsDf = self.imagePathsDf.set_index('case') 
        self.addCaseNamesToWidgets()


    def onRedViewComboboxChanged(self, volName):
        """Change which image is displayed in the red view"""
        self.setSliceViewVolume('Red', volName, self.volNodes[volName])


    def onGreenViewComboboxChanged(self, volName):
        """Change which image is displayed in the green view"""
        self.setSliceViewVolume('Green', volName, self.volNodes[volName])


    def onYellowViewComboboxChanged(self, volName):
        """Change which image is displayed in the yellow view"""
        self.setSliceViewVolume('Yellow', volName, self.volNodes[volName])


    def onRoiChanged(self, button):
        """Swith the visible ROI for all segmentations"""
        self.selectedLabelVal = self.labelNameToLabelVal[button.text]
        selectedLabelName = self.config['labelNames'][str(self.selectedLabelVal)]
        

    def onViewOrientationChanged(self, button):
        """Change orientation (ax/sag/cor) of all three slice views"""

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
        """Display file selection dialog and load selected paths in a DataFrame"""
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
            self.addCaseNamesToWidgets()


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


    def addCaseNamesToWidgets(self):
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
            self.nextCaseButton.enabled = True
            self.previousCaseButton.enabled = True
            self.selected_image_ind = 0
        else:
            self.selectDataButton.setText('Select Data Folders')
            self.caseComboBox.enabled = False
            self.nextCaseButton.enabled = False
            self.previousCaseButton.enabled = False
            self.selected_image_ind = None
            self.active_label_fn = None


    def nextCase(self):
        self.selected_image_ind += 1
        if self.selected_image_ind > len(self.imagePathsDf) - 1:
            self.selected_image_ind -= len(self.imagePathsDf)
        self.caseComboBox.setCurrentIndex(self.selected_image_ind)


    def previousCase(self):
        self.selected_image_ind -= 1
        if self.selected_image_ind < 0:
            self.selected_image_ind += len(self.imagePathsDf)
        self.caseComboBox.setCurrentIndex(self.selected_image_ind)


    def onCaseComboboxChanged(self, case_name):
        """Load a new case when the user selects from the cases combobox

        This is the main function for loading images from disk, configuring the views, and creating
        segmentations with the correct display names/colors.
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
        

    def setSliceViewVolume(self, sliceViewColor, volName, volNode):
        """Show the given `volNode` in the `sliceViewColor` slice view"""
        view = slicer.app.layoutManager().sliceWidget(sliceViewColor)
        view.sliceLogic().GetSliceCompositeNode().SetBackgroundVolumeID(volNode.GetID())
        view.sliceLogic().GetSliceCompositeNode().SetLinkedControl(True)
        view.mrmlSliceNode().RotateToVolumePlane(volNode)
        view.sliceController().setSliceVisible(True)  # show in 3d view
        

    def loadVolumesFromFiles(self, filename_dict):
        """Read and load images from dict of filenames. Keep references in self.volNodes"""
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

        selectedLabelName = self.config['labelNames'][str(self.selectedLabelVal)]
        
        # TEMP DEBUG
        self.selectedLabelVal = 2
        labelName = 'peritumoral edema'
        print('displaying all segs for ROI: ', selectedLabelName)
        print('displaying all segs for value:', self.selectedLabelVal)


        # create segs
        self.segmentations = {}
        self.segmentationNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLSegmentationNode', labelName)
        self.segmentationNode.SetReferenceImageGeometryParameterFromVolumeNode(list(self.volNodes.values())[0])
        self.segmentationNode.CreateDefaultDisplayNodes()
        slicer.mrmlScene.AddNode(self.segmentationNode)

        for seg_num, (labeler_name, seg_fn) in enumerate(seg_fns_dict.items()):

            # create labelmap
            if not seg_fn:
                continue
            labelmapNode = slicer.util.loadLabelVolume(seg_fn)
            if not labelmapNode:
                print('Failed to load label volume ', seg_fn)
                continue

            # Create new volume node for output
            sitkLabelmap = sitkUtils.PullVolumeFromSlicer(labelmapNode)
            slicer.mrmlScene.RemoveNode(labelmapNode)
            labelmap = sitk.GetArrayFromImage(sitkLabelmap)
            roiMask = (labelmap == self.selectedLabelVal).astype(np.uint8)

            # numpy array back to a simpleitk image
            roiMask = numpy_to_sitk_image(roiMask, sitkLabelmap) 

            # Use ITK filter to produce contour image/node
            contourImage = sitk.BinaryContourImageFilter().Execute(roiMask)
            contourNode = slicer.mrmlScene.AddNewNodeByClass('vtkMRMLLabelMapVolumeNode', labeler_name+' contours')
            sitkUtils.PushVolumeToSlicer(contourImage, contourNode)
            
            # create segmentation node from contour node
            slicer.vtkSlicerSegmentationsModuleLogic.ImportLabelmapToSegmentationNode(contourNode, self.segmentationNode)
            slicer.mrmlScene.RemoveNode(contourNode)


    def clearNodes(self):
        slicer.mrmlScene.Clear(0)


    def cleanup(self):
        self.clearNodes()
