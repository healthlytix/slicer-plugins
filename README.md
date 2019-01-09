A slicer module for quickly editing many binary segmentations.

The process of loading a segmentation from an image file, editing it in Slicer, and saving it to disk with the same geometry is an incredibly complex and error-prone process. This module is intended to make this workflow smoother and faster.


# Development

I followed [the instructions here](https://na-mic.org/wiki/2013_Project_Week_Breakout_Session:Slicer4Python) to create an extension and module from a template in [the Slicer repo](https://github.com/Slicer/Slicer). To enable this module, start slicer, open the "Edit" menu, select "Application Settings", click on "modules" in the side bar, and click the "Add" button in the "Additional module paths" box. Select the subfolder `BatchSegmenter` in the directory for this repo (ie, select `BatchSegmenter`, **not** the base repor directory).

Slicer includes a "developer mode" that allows you to reload your module without restarting the application. To turn it on, select from the menu `Edit > Application Settings`, choose "Developer" from the side bar and check the two boxes.

Helpful code snippets: https://www.slicer.org/wiki/Documentation/Nightly/ScriptRepository#Segmentations
