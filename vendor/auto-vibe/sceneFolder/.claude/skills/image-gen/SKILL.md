---
name: image-gen
description: Generate a single image from a text prompt, optionally guided by one or more reference images, at a requested ratio (e.g. 3:4, 16:9). Use when the user asks to create, generate, render, or transform an image.
---

# image-gen

Call `scripts/generate_image.sh` to generate an image. Pass three required arguments followed by optional reference image paths: `<ratio> <image_prompt> <output_path> [reference_image ...]`.

GPT Image 2 accepts image inputs for editing, restyling, compositing, and inpainting. Official references:

- [GPT Image 2 model](https://developers.openai.com/api/docs/models/gpt-image-2)
- [Image generation and editing guide](https://developers.openai.com/api/docs/guides/image-generation)
- [GPT Image prompting guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide)

Resolve the script path relative to this `SKILL.md`; cross-directory calls are supported.

```bash
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$SCRIPT_DIR/scripts/generate_image.sh" <ratio> <image_prompt> <output_path> [reference_image ...]
```

| Parameter | Description |
|---|---|
| ratio | Aspect-ratio string, such as `3:4`, `16:9`, or `1:1` |
| image_prompt | Image description (<= 1500 characters), including subject, style, and tone |
| output_path | Save path including filename; parent directories are created automatically |
| reference_image | Optional local image path; append up to five paths for multiple references |

Quote the second argument when it contains spaces or punctuation.

After the command finishes, run `ls -lh <output_path>` to confirm that the file exists.

## Prompt Writing

State the intended use, then describe the scene, subject, key details, and constraints in a consistent order. Use short labeled segments for complex requests. Make each image strong enough to serve as a hero frame: define the subject's distinctive state or action, shot and framing, spatial or scale relationship, lighting and value structure, material, palette, and intentional negative space.

Structure: `<intended use>, <scene and subject>, <shot / composition>, <spatial relationship and lighting>, <material / style / palette>, <constraints>`

Useful style vocabulary includes:

- **Flat / UI / vector**: `UI style`, `flat illustration`, `vector art`, `minimalist`, `clean geometric shapes`, `uniform fills`
- **Collage / paper cut**: `paper cut collage`, `layered flat cut-out shapes`, `torn paper edges`
- **Vintage / nostalgic**: `vintage paper collage`, `sun-faded tones`, `retro travel poster`
- **Realistic**: `photorealistic`, `documentary photography`, `film grain`
- **Other styles** as needed

## Editing and Reference Images

Treat every reference as a source image. Identify references by attachment order and give each one a role: subject, scene, composition, object, or style.

For a precise edit, separate the prompt into:

- **Goal**: the intended final result
- **Inputs**: what to take from each reference
- **Change**: the exact region, object, or property to modify
- **Preserve**: identity, pose, geometry, camera angle, framing, layout, lighting, typography, or other invariants
- **Integration**: perspective, scale, lighting, color temperature, contact shadows, and occlusion for composites

Make the smallest coherent change per pass and restate preservation requirements on each iteration. For text in the image, put the exact copy in quotes and specify placement, hierarchy, font character, and legibility.

## Examples

### 1. Realistic cat (3:4)

```bash
"$SCRIPT_DIR/scripts/generate_image.sh" 3:4 'a cat crouched on a narrow sunlit windowsill, close low-angle portrait with the silhouette breaking into bright sky, hard morning side light, photorealistic fine fur, muted warm palette, calm negative space above' public/img/realistic-cat.png
```

### 2. Cyberpunk city (16:9)

```bash
"$SCRIPT_DIR/scripts/generate_image.sh" 16:9 'a lone cyclist cutting across an immense rain-flooded intersection, very wide low-angle frame with towers leaning inward, cyan signage reflected as one diagonal path, photorealistic cyberpunk night, wet asphalt texture, open darkness ahead of the cyclist' public/img/cyberpunk-city.png
```

### 3. Santorini collage (1:1)

```bash
"$SCRIPT_DIR/scripts/generate_image.sh" 1:1 'whitewashed Santorini houses cascading around one oversized blue dome, steep top-down composition with the stairway forming a spiral, layered paper-cut collage, torn paper edges and olive-leaf shadows, chalk white and cobalt palette, clear sky pocket at upper right' public/img/santorini.png
```

### 4. Reference-guided restyle (16:9)

```bash
"$SCRIPT_DIR/scripts/generate_image.sh" 16:9 'Goal: restyle the source as a layered paper-cut collage. Input 1: subject and composition. Change: material treatment and palette to cobalt and warm white. Preserve: silhouette, camera angle, framing, and spatial layout.' public/img/restyled-scene.png public/img/source-scene.png
```
