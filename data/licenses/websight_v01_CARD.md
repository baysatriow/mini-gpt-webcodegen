---
language:
- en
license: cc-by-4.0
size_categories:
- 1M<n<10M
pretty_name: WebSight
dataset_info:
- config_name: v0.2
  features:
  - name: image
    dtype: image
  - name: text
    dtype: string
  - name: llm_generated_idea
    dtype: string
  splits:
  - name: train
    num_bytes: 368943620718.125
    num_examples: 1922671
  download_size: 144861710051
  dataset_size: 368943620718.125
- config_name: v0.1
  features:
  - name: image
    dtype: image
  - name: text
    dtype: string
  splits:
  - name: train
    num_bytes: 35386660486.65
    num_examples: 822987
  download_size: 31394170440
  dataset_size: 35386660486.65
configs:
- config_name: v0.2
  default: true
  data_files:
  - split: train
    path: v0.2/train-*
- config_name: v0.1
  data_files:
  - split: train
    path: data/train-*
tags:
- code
- synthetic
---
# Dataset Card for WebSight


## Dataset Description

WebSight is a large synthetic dataset containing HTML/CSS codes representing synthetically generated English websites, each accompanied by a corresponding screenshot.

This dataset serves as a valuable resource for tasks such as generating UI codes from a screenshot.

It comes in two versions:
 - v0.1: Websites are coded with HTML + CSS. They do not include real images.
 - v0.2: Websites are coded with HTML + Tailwind CSS. They do include real images.

Essentially, here are the improvements in version v0.2, compared to version v0.1:
- Websites include real images (related to the context of the website!!)
- Usage of Tailwind CSS instead of traditional CSS
- Contains 2x more examples
- Contains more tables
- Better resolution for the screenshots
- Presence of a column indicating the LLM-generated idea to create the websites

<details>
  <summary>Details for WebSight-v0.1 (HTML + CSS)</summary>

## Data Fields

An example of a sample appears as follows:
```
{
    'images': PIL.Image,
    'text': '<html>\n<style>\n{css}</style>\n{body}\n</html>',
}
```
where `css` is the CSS code, and `body` is the body of the HTML code.
In other words, the CSS code is embedded directly within the HTML code, facilitating the straightforward training of a model.

## Data Splits

There is only one split, `train`, that contains 822,987 images and codes.

## Dataset Creation

This dataset was created using [Mistral-7B-v0.1](https://huggingface.co/mistralai/Mistral-7B-v0.1) to generate random website ideas with the prompt
```
Generate diverse website layout ideas for different companies, each with a unique design element.
Examples include: a car company site with a left column, a webpage footer with a centered logo.
Explore variations in colors, positions, and company fields.
Don't give any explanations or recognition that you have understood the request,
just give the list of 10 ideas, with a line break between each.
```
which were then passed to [Deepseek-Coder-33b-Instruct](https://huggingface.co/deepseek-ai/deepseek-coder-33b-instruct) with the prompt
```
Create a very SIMPLE and SHORT website with the following elements: {idea}
Be creative with the design, size, position of the elements, columns, etc...
Don't give any explanation, just the content of the HTML code `index.html` starting with `<!DOCTYPE html>`,
followed by the CSS code `styles.css` starting with `/* Global Styles */`.
Write real and short sentences for the paragraphs, don't use Lorem ipsum.
When you want to display an image, don't use <img> in the HTML, always display a colored rectangle instead. 
```
Following these steps, the HTML and CSS codes were extracted from the outputs of Deepseek-Coder and formatted into the structure `'<html>\n<style>\n{css}</style>\n{body}\n</html>'`.

</details>

<details>
  <summary>Details for WebSight-v0.2 (HTML + Tailwind CSS)</summary>

## Data Fields

An example of a sample appears as follows:
```
{
    'images': PIL.Image,
    'text': '<html>\n<link href="https://cdn.jsdelivr.net/npm/tailwindcss@2.2.19/dist/tailwind.min.css" rel="stylesheet">\n{body}\n</html>',
}
```
where `body` is the body of the HTML code, containing directly the Tailwind CSS code and facilitating the straightforward training of a model.

## Data Splits

There is only one split, `train`, that contains TO DO images and codes.

## Dataset Creation

TO DO.

For now, the creation of the dataset is documented in the technical report.
</details>

## Terms of Use

By using the dataset, you agree to comply with the original licenses of the source content as well as the dataset license (CC-BY-4.0). Additionally, if you use this dataset to train a Machine Learning model, you agree to disclose your use of the dataset when releasing the model or an ML application using the model.

### Licensing Information

License CC-BY-4.0.

### Citation Information

If you are using this dataset, please cite our [technical report](https://arxiv.org/abs/2403.09029)
```
@misc{laurençon2024unlocking,
      title={Unlocking the conversion of Web Screenshots into HTML Code with the WebSight Dataset}, 
      author={Hugo Laurençon and Léo Tronchon and Victor Sanh},
      year={2024},
      eprint={2403.09029},
      archivePrefix={arXiv},
      primaryClass={cs.HC}
}
```