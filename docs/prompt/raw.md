I want to create an application to extract key screenshots and notes from conferences speeches, typically Microsoft Build (incoming tomorrow) and Ignite. 

Input: URL of the videos, could be from the website (e.g. Microsoft Build and Ignite) or youtube. Because these conferences are public, the videos will be posted to Youtube as well but there will be a bit of time lag.

Output: md files with screenshots and keynotes. 

Requirements:
This stack should explore usage of the best-in-class services for any component. Better to be in Azure but if any other services really stand out (e.g. image analysis), we should consider using as well.

Latency is acceptable given the input is an video. However, it is preferable if we can keep the latency minimum so that users don't expire their patience.

This application should include frontend, backend, deployment and cicd.

It is an art of how detailed the screenshots and keynotes should be. It could be at high-level, and could be very detailed. My personal habbit is to capture it in very detail if it is new and I am learning. As of that, a more reasonable approach would be for example, take the full transcription, clean up and break down into reasonable sections, and take screenshots based on the section; this could be better performance than the other way around (take screenshot first and then put transcription).