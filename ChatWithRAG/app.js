import { useState } from "react";

function App() {
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState("");
  const [loading, setLoading] = useState(false);
  const askQuestion = async () => {
    setLoading(true);
    const res = await fetch("http://localhost:8000/ask", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ question })
    });
    const data = await res.json();
    setAnswer(data.answer);
    setLoading(false);
  };
  return (
    <div style={{ padding: "2rem", maxWidth: "600px", margin: "auto" }}>
      <h2>Chat with your PDF</h2>
      <textarea
        value={question}
        onChange={(e) => setQuestion(e.target.value)}
        rows={4}
        style={{ width: "100%" }}
        placeholder="Ask a question about the PDF"
      />
      <button onClick={askQuestion} disabled={loading}>
        {loading ? "Thinking..." : "Ask"}
      </button>
      <div style={{ marginTop: "1rem" }}>
        <strong>Answer</strong>
        <p>{answer}</p>
      </div>
    </div>
  );
}
export default App;