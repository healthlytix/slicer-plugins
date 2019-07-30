A slicer module for quickly editing many binary segmentations.

The process of loading a segmentation from an image file, editing it in Slicer, and saving it to disk with the same geometry is a complex and error-prone process. This module is intended to make this workflow smoother and faster.

# Installation

Clone this repo to your computer. In the Slicer menu, select `Edit > Application Setttings` and select `Modules` from the side pane. Next to `Additional Module Paths` are buttons to `Add` and `Remove` module paths. Click the `Add` button, and select the `BatchSegmentation` subfolder in this repo (NOT the repo root). You will be prompted to restart Slicer; do so. Once it has restarted, you should be able to select the `Batch Segmentation` module from the `Modules` combobox.

# Development

I followed [the instructions here](https://na-mic.org/wiki/2013_Project_Week_Breakout_Session:Slicer4Python) to create an extension and module from a template in [the Slicer repo](https://github.com/Slicer/Slicer). 

Slicer includes a "developer mode" that allows you to reload your module without restarting the application. To turn it on, select from the menu `Edit > Application Settings`, choose "Developer" from the side bar and check the two boxes.

Helpful code snippets: https://www.slicer.org/wiki/Documentation/Nightly/ScriptRepository#Segmentations