import { Config } from "@remotion/cli/config";

Config.setVideoImageFormat("jpeg");
Config.setOverwriteOutput(true);

// Output directory for renders
Config.setOutputLocation("out/sentinel-demo.mp4");
