
# Data Visualization: Principles and Storytelling
**Author:** Vo Nhat Tan

---

## Part 1: Principles of Data Visualization

### 1. Visual Processing and Perceptual Rankings
The accuracy with which a reader perceives data values depends on the visual encoding used. Alberto Cairo's perceptual ranking (from most accurate to general estimates) is as follows:

1.  **Position along a common scale:** Highest accuracy (e.g., standard bar and line charts).
2.  **Position along identical, non-aligned scales:** High accuracy but increased cognitive load.
3.  **Length:** Magnitude encoded by lines/bars.
4.  **Direction/Slope:** Magnitude via angles or segments.
5.  **Angle:** Angular differences (e.g., pie charts).
6.  **Parts of a whole:** Proportional segments.
7.  **Area:** Two-dimensional size (e.g., bubble charts).
8.  **Volume:** Three-dimensional representations.
9.  **Shading and Saturation:** Differences in intensity (e.g., heatmaps).
10. **Color Hue:** Suitable for general patterns, not precise comparison.

#### Visual Encoding Summary Table
| Visual Encoding Type | Description | Primary Perceptual Problem | Implications for Interpretation |
| :--- | :--- | :--- | :--- |
| **Position Along a Common Scale** | Data points share a common axis/baseline. | Distortion from truncated or manipulated axes. | Highly accurate; vulnerable to scale manipulation. |
| **Position Along Non-Aligned Scales** | Data on separate axes without shared baseline. | Lack of common reference impairs direct comparison. | May create illusory correlations. |
| **Length** | Magnitude encoded by length of bars/lines. | Non-zero baselines exaggerate differences. | Moderately reliable but less precise than aligned scales. |
| **Area** | Magnitude represented by 2D size. | Perception is nonlinear; viewers often misjudge proportions. | Frequently leads to over- or underestimation. |
| **Volume and Curvature** | 3D representations with depth/perspective. | Perspective distortion and occlusion obscure accuracy. | Adds aesthetic complexity without informational benefit. |
| **Shading and Color Saturation** | Magnitude encoded via hue or intensity. | Color discrimination is context-dependent and imprecise. | Suitable for general patterns, not precise quantitative comparison. |

### 2. Anscombe's Quartet
Anscombe's Quartet demonstrates the importance of visualizing data. It consists of four datasets that have nearly identical descriptive statistics (mean, variance, correlation, and regression line) but appear very different when graphed, revealing distinct patterns and outliers.

### 3. Gestalt Principles of Visual Perception
These principles describe how humans naturally organize visual elements into groups:
* **Proximity:** Objects close together are perceived as a group.
* **Similarity:** Objects with similar characteristics (shape, color) are perceived as a group.
* **Enclosure:** Objects within a boundary are seen as belonging together.
* **Closure:** People perceive incomplete shapes as whole entities based on prior constructs.
* **Continuity:** Elements on a line or curve are perceived as related.
* **Connection:** Elements physically linked by lines are perceived as a group more strongly than by color or shape.

### 4. Guidelines for Better Data Visualizations
1.  **Show the Data:** Determine the right amount of data and the best way to present it.
2.  **Reduce the Clutter:** Remove legends when possible and label data directly to reduce cognitive load.
3.  **Avoid the Spaghetti Chart:** Use small multiples or separate charts instead of overlapping too many lines.
4.  **Start with Gray:** Begin with neutral tones and use color strategically to focus the audience's attention.
5.  **Don't Overcomplicate:** Use consistent, legible fonts and straightforward language. Favor simplicity over complexity.

---

## Part 2: Storytelling with Data Visualization

### 1. The Importance of Context
Analysis can be categorized into two types:
* **Exploratory Analysis:** Analysis in search of insights (solitary).
* **Explanatory Analysis:** Presentation with a fixed message (one-way communication or dialogue).

#### The "Who, What, How" of Explanatory Analysis
* **WHO:** To whom are you communicating?
* **WHAT:** What do you want your audience to know or do?
* **HOW:** How can you use data to help make your point?

### 2. Constructing the Story
#### The 3-Minute Story and Big Idea
* **3-Minute Story:** A concise summary of what the audience needs to know if time is limited.
* **Big Idea:** A single, complete sentence that clearly shows your perspective and explains what is at risk/why it matters.

#### Story Structure
* **The Beginning:** Introduce the plot and build context (setting, characters, imbalance, balance, and solution). Frame the story in terms of the audience's needs.
* **The Middle:** Clearly show the problem, explain the solution, and convince the audience why your recommended action is correct.
* **The End:** Provide a clear call to action.

### 3. Choosing an Effective Visual
To visualize data effectively, understand the data types and preattentive attributes.

#### Types of Data
* **Qualitative (Categorical):**
    * *Nominal:* Symbols or names (label variables).
    * *Binary:* Only two states (absent/present).
    * *Ordinal:* Meaningful order/ranking, but magnitude between values is unknown.
* **Quantitative (Numerical):**
    * *Interval:* Ordered and measurable, but no true zero-point (e.g., temperature).
    * *Ratio:* Ordered, measurable, and has a true zero-point.

#### Preattentive Attributes
These are visual properties processed by our brains almost instantly:
* **Form:** Shape, Enclosure, Line Width, Size, Markings, Orientation, Curvature, Sharpness.
* **Color:** Saturation, Hue.
* **Spatial Position:** Position, 2D/3D Density.

#### Use of Color in Data Visualization
* **Sequential:** Color ordered from light to dark (e.g., sales volume).
* **Diverging:** Two sequential colors with a neutral midpoint (e.g., positive vs. negative sentiment).
* **Categorical:** Contrasting hues for individual comparisons (e.g., different product categories).
* **Highlight:** Used to make a specific data point stand out.
* **Alert:** Bright, alarming colors (like red/orange) to warn the reader of issues.

### 4. Page Layout and Information Consumption
* **The Z-Pattern:** Readers typically take in information on a page or screen in a zigzag "Z" pattern. Place the most important information where the eye naturally travels first.

---
**Contact Information:** vntan.work@gmail.com
