A slicer module for quickly editing many binary segmentations.

The process of loading a segmentation from an image file, editing it in Slicer, and saving it to disk with the same geometry is an incredibly complex and error-prone process. This module is intended to make this workflow smoother and faster.


# Development

I followed [the instructions here](https://na-mic.org/wiki/2013_Project_Week_Breakout_Session:Slicer4Python) to create an extension and module from a template in [the Slicer repo](https://github.com/Slicer/Slicer). If you are on a mac and you installed the binary in the usual way, your app will be at `/Applications/Slicer.app`. In order to allow Slicer to see the new module, you must start it with the `--additional-module-paths` option, i.e., `open -n /Applications//Slicer.app --args --additional-module-paths <path/to/this/repo>/VolumeScroller`. 

Slicer includes a "developer mode" that allows you to reload your module without restarting the application. To turn it on, select from the menu `Edit > Application Settings`, choose "Developer" from the side bar and check the two boxes.
