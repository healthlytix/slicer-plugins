A slicer module for quickly editing many binary segmentations.

The process of loading a segmentation from an image file, editing it in Slicer, and saving it to disk with the same geometry is a complex and error-prone process. This module is intended to make this workflow smoother and faster.

# Installation

Clone this repo to your computer. In the Slicer menu, select `Edit > Application Setttings` and select `Modules` from the side pane. Next to `Additional Module Paths` are buttons to `Add` and `Remove` module paths. Click the `Add` button, and select the `BatchSegmentation` or `SegReview` subfolder in this repo (NOT the repo root). You will be prompted to restart Slicer; do so. Once it has restarted, you should be able to select the newly-installed module from the `Modules` combobox.

# Usage

## Batch Segmentation

* Open the `Batch Segmentation Editor` module.
* Click on the `Select Data Folders` button and select all of the folders that you want to work on. If this step is successful, the module will load the image names into the `Activate Folder` combobox, and will load the first image and segmentation.
* Switch to the `Segment Editor` module. From the `Master Volume` select the your reference image (it should be the only choice) and edit the segmentation as you see fit. Instructions for use [can be found here](https://slicer.readthedocs.io/en/latest/user_guide/module_segmenteditor.html). Common keyboard shortcuts: `1` to select paintbrush, `3` to select eraser, `space` to toggle between the 2 most recently used tools. Once the focus is in the slicer viewer, you can toggle the segmentation visibility with `g`.
* When you are done with the segmentation, switch bach to `Batch Segmentation` and select the next image you'd like to work on. The segmentation you were just working on is automatically saved.

## SegReview

This is quite similar to BatchSegmentation, but the segmentations are not editable.

## CompareSegs

Compare multiple segmentations against one another, one ROI at a time. The data is expected to be organized like so:

```
segmentations
├── labeler1
│   ├── case1
│   │   ├── im1.nii
│   │   ├── im2.nii
│   │   └── seg.nii
...
│   ├── case2
│   │   ├── im1.nii
│   │   ├── im2.nii
│   │   └── seg.nii
...
├── labeler2
│   ├── case1
│   │   ├── im1.nii
│   │   ├── im2.nii
│   │   └── seg.nii
...
│   ├── case2
│   │   ├── im1.nii
│   │   ├── im2.nii
│   │   └── seg.nii
...
```

In this example, you'd load the data folders `labeler1` and `labeler2`. For each case, the module will display the 3 image files specified in the config and will create one segmentation for each labeler. Each labeler gets a different color and all ROIs for that labelers segmentation share the same color, so it only makes sense to view one ROI at a time.

# Development

I followed [the instructions here](https://na-mic.org/wiki/2013_Project_Week_Breakout_Session:Slicer4Python) to create an extension and module from a template in [the Slicer repo](https://github.com/Slicer/Slicer).

Slicer includes a "developer mode" that allows you to reload your module without restarting the application. To turn it on, select from the menu `Edit > Application Settings`, choose "Developer" from the side bar and check the two boxes.

Helpful code snippets: https://www.slicer.org/wiki/Documentation/Nightly/ScriptRepository#Segmentations

## TODO

* Give human-readable names to the segments
* standard seg editor keyboard shortcuts don't work. There's a snippet [here](https://www.slicer.org/wiki/Documentation/Nightly/ScriptRepository#Segmentations) showing how to do this for paint tool
* Scroll to tumor center?
