import os
import argparse
from moviepy.editor import VideoFileClip, CompositeVideoClip


def blend_single_video(video1_path, bg_videos, index, compress, save_folder):
    """مزج فيديو تأثير واحد مع عدة خلفيات"""
    try:
        clip1 = VideoFileClip(video1_path).resize(height=720).set_position("center")
        final_clips = []
        for i, bg_path in enumerate(bg_videos):
            bg_clip = (
                VideoFileClip(bg_path)
                .resize(height=720)
                .set_duration(clip1.duration)
            )
            comp = CompositeVideoClip([bg_clip, clip1.set_start(0)])
            out_path = os.path.join(
                save_folder, f"blend_{index}_{i+1}.mp4"
            )
            codec = "libx265" if compress else "libx264"
            comp.write_videofile(
                out_path,
                codec=codec,
                audio_codec="aac",
                threads=4,
                preset="fast",
                fps=30,
                verbose=False,
                logger=None,
            )
            final_clips.append(out_path)
        return final_clips
    except Exception as e:
        print(f"❌ خطأ أثناء مزج {video1_path} : {e}")
        return []


def list_videos_from(path):
    """إرجاع قائمة ملفات الفيديو من مجلد"""
    if not os.path.exists(path):
        return []
    exts = (".mp4", ".mov", ".avi", ".mkv")
    return [
        os.path.join(path, f)
        for f in sorted(os.listdir(path))
        if f.lower().endswith(exts)
    ]


def main():
    parser = argparse.ArgumentParser(description="Quran Video Tool (headless)")
    parser.add_argument(
        "--input1", type=str, help="مجلد للفيديوهات الأساسية (التأثيرات)", default="inputs/video1"
    )
    parser.add_argument(
        "--input2", type=str, help="مجلد للخلفيات", default="inputs/video2"
    )
    parser.add_argument(
        "--output", type=str, help="مجلد الحفظ", default="outputs"
    )
    parser.add_argument(
        "--per-bg", type=int, help="عدد فيديوهات التأثير لكل خلفية", default=3
    )
    parser.add_argument(
        "--compress", action="store_true", help="ضغط الفيديوهات الناتجة بـ H.265"
    )
    args = parser.parse_args()

    video1_paths = list_videos_from(args.input1)
    video2_paths = list_videos_from(args.input2)
    os.makedirs(args.output, exist_ok=True)

    if not video1_paths or not video2_paths:
        print("❌ لم يتم العثور على فيديوهات في المجلدات المدخلة.")
        return

    try:
        per_bg = args.per_bg
        bg_pointer = 0
        for idx, video1 in enumerate(video1_paths):
            if idx % per_bg == 0:
                bg_index = bg_pointer % len(video2_paths)
                main_bg = video2_paths[bg_index]
                bg_pointer += 1

            background_list = video2_paths[bg_index + 1 :] + video2_paths[:bg_index]
            selected_bgs = [main_bg] + list(background_list)

            print(f"[{idx+1}/{len(video1_paths)}] جاري معالجة: {os.path.basename(video1)}")
            blend_single_video(video1, selected_bgs, idx + 1, args.compress, args.output)

        print("✅ اكتمل العمل بنجاح.")

    except Exception as e:
        print("❌ خطأ عام:", e)
        raise


if __name__ == "__main__":
    main()
