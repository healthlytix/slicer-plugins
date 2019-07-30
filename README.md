A slicer module for quickly editing many binary segmentations.

The process of loading a segmentation from an image file, editing it in Slicer, and saving it to disk with the same geometry is a complex and error-prone process. This module is intended to make this workflow smoother and faster.

# Installation

Clone this repo to your computer. In the Slicer menu, select `Edit > Application Setttings` and select `Modules` from the side pane. Next to `Additional Module Paths` are buttons to `Add` and `Remove` module paths. Click the `Add` button, and select the `BatchSegmentation` subfolder in this repo (NOT the repo root). You will be prompted to restart Slicer; do so. Once it has restarted, you should be able to select the `Batch Segmentation` module from the `Modules` combobox.

# Usage

* Open the `Batch Segmentation` module. 
* In the `Image Names` and `Label Names` boxes, add paths to your images using wildcards. Typical `Image Names` will look like `/path/to/images/*.nii` and `Label Names` will be like `/path/to/labels/*.nii`. Label images and reference images are expected to have the same names, but be stored in separate folders. If this step is successful, the module will load the image names into the `Activate Volume` combobox, and will load the first image and segmentation.
* Switch to the `Segment Editor` module. From the `Master Volume` select the your reference image (it should be the only choice) and edit the segmentation as you see fit. Instructions for use [can be found here](https://slicer.readthedocs.io/en/latest/user_guide/module_segmenteditor.html). Common keyboard shortcuts: `1` to select paintbrush, `3` to select eraser, `space` to toggle between the 2 most recently used tools. Once the focus is in the slicer viewer, you can toggle the segmentation visibility with `g`.
* When you are done with the segmentation, switch bach to `Batch Segmentation` and select the next image you'd like to work on. The segmentation you were just working on is automatically saved. 

# Development

I followed [the instructions here](https://na-mic.org/wiki/2013_Project_Week_Breakout_Session:Slicer4Python) to create an extension and module from a template in [the Slicer repo](https://github.com/Slicer/Slicer). 

Slicer includes a "developer mode" that allows you to reload your module without restarting the application. To turn it on, select from the menu `Edit > Application Settings`, choose "Developer" from the side bar and check the two boxes.

Helpful code snippets: https://www.slicer.org/wiki/Documentation/Nightly/ScriptRepository#Segmentations