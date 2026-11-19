import { useState } from "react";

import { PageLayout } from "./workspacePages";

const foodDataApi = "https://api.nal.usda.gov/fdc/v1/foods/search?api_key=DEMO_KEY";

export function Nutrition() {
  const [query, setQuery] = useState("");
  const [foods, setFoods] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [searched, setSearched] = useState(false);

  async function searchFoods(event) {
    event.preventDefault();
    const searchTerm = query.trim();
    if (!searchTerm) {
      setError("Enter a food name to search.");
      setFoods([]);
      setSearched(false);
      return;
    }

    setLoading(true);
    setError("");
    setFoods([]);
    setSearched(false);
    try {
      const response = await fetch(foodDataApi, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ query: searchTerm, pageSize: 8 }),
      });
      if (!response.ok) {
        throw new Error(
          response.status === 429
            ? "USDA demo API rate limit reached. Try again later."
            : `USDA FoodData Central returned HTTP ${response.status}.`,
        );
      }

      const data = await response.json();
      setFoods(data.foods || []);
      setSearched(true);
    } catch (searchError) {
      setError(searchError.message || "Could not reach USDA FoodData Central.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <PageLayout
      title="Bone-supportive Nutrition"
      description="Search public food-composition data and explore general nutrition education."
      icon="🥗"
    >
      <div className="product-panel nutrition-panel">
        <form className="nutrition-search" onSubmit={searchFoods}>
          <label htmlFor="food-search">Search foods</label>
          <div>
            <input
              id="food-search"
              type="search"
              value={query}
              onChange={(event) => setQuery(event.target.value)}
              placeholder="Try yogurt, tofu, or salmon"
            />
            <button className="primary-button" type="submit" disabled={loading}>
              {loading ? "Searching..." : "Search USDA"}
            </button>
          </div>
        </form>

        {error && <div className="alert error">{error}</div>}
        {searched && foods.length === 0 && (
          <p className="muted-note">No matching foods were returned.</p>
        )}
        {foods.length > 0 && (
          <div className="food-results">
            {foods.map((food) => (
              <article className="food-result" key={food.fdcId}>
                <div>
                  <h3>{food.description}</h3>
                  <span>{food.dataType || "USDA FoodData Central"}</span>
                </div>
                <div className="food-nutrients">
                  <Nutrient food={food} name="Calcium, Ca" />
                  <Nutrient food={food} name="Vitamin D" />
                </div>
              </article>
            ))}
          </div>
        )}
      </div>

      <div className="product-panel feature-disclaimer">
        <strong>General education only</strong>
        <p>
          Nutrient values depend on the food record and serving basis. This
          prototype does not make personalized diet recommendations. Consult a
          qualified health professional for advice about an individual diet.
        </p>
        <a href="https://fdc.nal.usda.gov/" target="_blank" rel="noreferrer">
          Source: USDA FoodData Central (public-domain data)
        </a>
        <small>
          Uses the USDA demonstration key, which has low request limits. Search
          terms are sent to USDA; scan files are not.
        </small>
      </div>
    </PageLayout>
  );
}

function Nutrient({ food, name }) {
  const nutrient = (food.foodNutrients || []).find((item) =>
    item.nutrientName?.toLowerCase().includes(name.toLowerCase()),
  );

  return (
    <div>
      <span>{name.startsWith("Calcium") ? "Calcium" : "Vitamin D"}</span>
      <strong>
        {nutrient ? `${nutrient.value} ${nutrient.unitName}` : "Not listed"}
      </strong>
    </div>
  );
}

const lessons = [
  {
    id: "structure",
    title: "How bones are built",
    summary: "Learn about the living tissue and structure of the skeleton.",
    paragraphs: [
      "Bone is living tissue that is continually renewed. Its outer layer is dense, while inner regions contain a lighter, honeycomb-like structure.",
      "The skeleton supports movement and protects organs. Bone marrow inside some bones produces blood cells.",
    ],
    source: "https://medlineplus.gov/ency/article/002249.htm",
    sourceLabel: "MedlinePlus: Bones",
    question: "Which statement about bone is true?",
    answers: [
      "Bone is living tissue that changes over time.",
      "Bone is an inert material that never changes.",
      "All bones have the same internal structure.",
    ],
    correct: 0,
  },
  {
    id: "imaging",
    title: "Understanding bone imaging",
    summary: "A simple guide to X-rays, CT images, and 3D views.",
    paragraphs: [
      "An X-ray is a two-dimensional projection. Overlapping anatomy can affect what is visible in that projection.",
      "CT scanners collect many X-ray measurements from different angles to create cross-sectional images. A 3D view is a visualization derived from image data; it is not automatically a diagnosis.",
    ],
    source: "https://medlineplus.gov/ency/article/003337.htm",
    sourceLabel: "MedlinePlus: CT scan",
    question: "What does a 3D visualization represent?",
    answers: [
      "A visualization derived from image data.",
      "A guaranteed medical diagnosis.",
      "A replacement for review by a qualified professional.",
    ],
    correct: 0,
  },
  {
    id: "bone-health",
    title: "Everyday bone health",
    summary: "Explore general topics related to bone health and learning.",
    paragraphs: [
      "Bone health is influenced by many factors, including age, health history, activity, and nutrition. General information cannot account for an individual's needs.",
      "Questions about symptoms, supplements, medicines, or a personal scan should be discussed with a qualified health professional.",
    ],
    source: "https://www.niams.nih.gov/health-topics/osteoporosis",
    sourceLabel: "NIAMS: Osteoporosis",
    question: "Where should a personal scan or treatment question go?",
    answers: [
      "To a qualified health professional.",
      "To an online quiz.",
      "To a general food search.",
    ],
    correct: 0,
  },
];

export function BoneAcademy() {
  const [selectedId, setSelectedId] = useState(lessons[0].id);
  const [answer, setAnswer] = useState(null);
  const lesson = lessons.find((item) => item.id === selectedId);

  function selectLesson(id) {
    setSelectedId(id);
    setAnswer(null);
  }

  return (
    <PageLayout
      title="Bone Academy"
      description="Short, source-linked lessons about bones, imaging, and learning."
      icon="🦴"
    >
      <div className="academy-layout">
        <nav className="product-panel academy-lessons" aria-label="Bone Academy lessons">
          <h2>Lessons</h2>
          {lessons.map((item) => (
            <button
              className={selectedId === item.id ? "selected" : ""}
              key={item.id}
              type="button"
              onClick={() => selectLesson(item.id)}
            >
              <strong>{item.title}</strong>
              <span>{item.summary}</span>
            </button>
          ))}
        </nav>

        <article className="product-panel academy-content">
          <h2>{lesson.title}</h2>
          {lesson.paragraphs.map((paragraph) => <p key={paragraph}>{paragraph}</p>)}
          <a href={lesson.source} target="_blank" rel="noreferrer">
            {lesson.sourceLabel}
          </a>

          <section className="academy-quiz">
            <h3>Quick check</h3>
            <p>{lesson.question}</p>
            {lesson.answers.map((option, index) => (
              <button
                className={answer === index ? "selected" : ""}
                key={option}
                type="button"
                onClick={() => setAnswer(index)}
              >
                {option}
              </button>
            ))}
            {answer !== null && (
              <p className={answer === lesson.correct ? "quiz-feedback correct" : "quiz-feedback"}>
                {answer === lesson.correct
                  ? "Correct."
                  : "Not quite. Review the lesson and try again."}
              </p>
            )}
          </section>
        </article>
      </div>

      <p className="feature-disclaimer academy-disclaimer">
        Educational content only; it is not medical advice or a substitute for
        professional care.
      </p>
    </PageLayout>
  );
}
