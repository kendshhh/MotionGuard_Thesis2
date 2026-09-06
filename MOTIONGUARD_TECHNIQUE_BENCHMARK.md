# MotionGuard Beginner Technique Benchmark

## Selection criteria

The first techniques must be appropriate for beginners, safely rehearsed in an open area, observable by a single front-facing RGB camera, distinguishable using shoulders/elbows/wrists/hips, and easy to record as repeatable sequences. They are training simulations only; they do not replace trainer instruction or personal-safety judgment.

## Recommended Beginner catalogue

| ID | Approved working name | Why it is suitable for V1 | Trainer boundary |
| --- | --- | --- | --- |
| `punch` | Controlled Straight Punch | Clear single-arm extension and elbow-angle change; distinguishable from the block and exit sequences. | Record at low speed into open space; trainer defines stance, hand position, and safe range. |
| `block` | Two-Arm High Block | Both forearms move toward an elevated guard, giving reliable bilateral landmarks. | Trainer defines the exact guard position and prevents unsafe joint extension. |
| `escape` | Protective Step-Back Exit | Captures a guarded posture plus a controlled backward/sideward exit, aligning the game with the self-protection goal of creating distance. | Practice only in a cleared area; trainer defines the movement and balance requirements. |

## Benchmark conclusion

These three movements retain the proposal's existing Punch, Block, and Escape categories while using precise display names. They cover one unilateral arm motion, one bilateral guard motion, and one mobility/exit motion, which reduces confusion during DTW classification. They are a sensible first recording set before the three trainer-selected higher-tier techniques.

The catalogue deliberately remains disabled until a qualified trainer records, reviews, and approves each reference sequence. Government self-defense programs in the Philippines commonly pair practical instruction with situational awareness, risk assessment, and escape/de-escalation rather than presenting physical techniques as a complete safety solution. [DOLE Institute for Labor Studies](https://ils.dole.gov.ph/policy-advocacies/media-resources/news/ils-promotes-personal-safety-with-hands-on-self-defense-training) and [Isabela City/PIA](https://pia.gov.ph/news/mindanao/zp/isabela-city-women-learn-self-defense/) support that framing. MediaPipe's Pose Landmarker supplies the required 33 body landmarks, including shoulder, elbow, wrist, and hip points used by the V1 feature extractor. [Google AI Edge documentation](https://developers.google.com/edge/mediapipe/solutions/vision/pose_landmarker)

## Recording protocol

1. A qualified trainer chooses the final form and demonstrates it slowly in a cleared, well-lit space.
2. Record at least three clean trials per technique; retain only sequences with at least 18 valid frames.
3. Review the captured skeletal playback and select the best trainer-approved trial.
4. Export the selected sequence to Unity; set `trainerApproved` and `readyForEvaluation` to `true` only after the trainer's approval is documented.
