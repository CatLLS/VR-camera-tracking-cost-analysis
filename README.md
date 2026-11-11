Group: Cat(me), Thomas, Sarms, Caue

Later I'll do a better readme, here's the overview:

Google Cardboard is a more affordable VR option (the headset uses your smartphone and costs around 50 reais), but it lacks sensors to track your position within a room and runs entirely on the phone, which limits both the experience and performance. Some users opt for "PC VR," where a PC runs the game and streams it to a smartphone/Cardboard headset; however, this setup also lacks the spatial tracking found in more expensive VR headsets.

Spatial tracking is crucial—not only for the overall experience but also for reducing motion sickness. With it, moving around your physical space translates into movement within the game—unlike other VR locomotion methods, such as using a joystick or continuous movement (where you are constantly "walking" forward, controlling your direction only with your head or a joystick).

To make better, more immersive locomotion accessible at a lower cost, software solutions (utilizing AI) have emerged that determine your position in a room—using either your smartphone’s camera or a PC webcam—to enable movement within a VR environment.

Me and my friends want to test how using these tools alongside a game affects the smartphone's performance, given that the games themselves would be running on the device. (We are not pursuing PC VR, as it falls outside the scope of our project and we wouldn't have enough time.)

So, we need to build a web application for mobile (time constraints) that allows us to easily capture the data for analysis. We want to be able to test things all within the app and maybe click to export the data as a .txt or .db (whatever works best) to analyze later. 

Here's my professor's opinion for you to keep in mind:
The topic is really great, and I believe it’s definitely feasible within the timeframe, provided you narrow down the scope now. You can keep the headset, locomotion, and the full game as your broader motivation; however, I recommend simplifying the core problem to measuring the performance cost—specifically, the impact on frame time—when a single smartphone runs a 3D scene while simultaneously using its camera for environmental tracking. This week, conduct a feasibility test: run the scene both with and without the tracker enabled, and measure the frame time in milliseconds (on Android, you can use a tool like Perfetto). First, verify whether the system allows the tracker to access the camera while the game is running in the foreground—this is a potential pain point. If it causes issues, try building a single application that integrates both the camera and the 3D content, or use a synthetic workload instead of the actual game. To refine your research question, consider this: what is the performance cost (measured in p95 frame time, in ms) of running the tracker alongside the game, as the workload varies (e.g., tracker off, camera at low resolution, camera at high resolution)? Potential mechanisms to investigate include task scheduling across different workloads and thermal throttling (frequency reduction due to heat). This also opens up several avenues for the four of you to explore, such as frame time, per-core CPU usage, performance degradation over a 15-minute period, and battery consumption. I strongly suggest excluding PCVR, as well as comparisons between different smartphones or building a game from scratch. Remember to update "Block P" with your final decisions. Good luck!

I also need you to fill the project form on the notes folder.

for more context about the assignment, why and what we need to measure, check the notes folder.

if you have questions about implementation or literally anything just call me. Don't make any decision without asking me.