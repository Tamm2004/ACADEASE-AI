import React from "react";

const TYPE_LABEL = {
  note: "Notes",
  pyq: "PYQ",
  youtube: "YouTube",
  book: "Book",
  website: "Website",
  practice: "Practice",
  other: "Resource",
};

export default function ResourceCard({ item }) {
  const metaParts = [];
  if (item.subject) metaParts.push(item.subject);
  if (item.semester) metaParts.push(`Sem ${item.semester}`);
  if (item.exam_type) metaParts.push(item.exam_type);
  if (item.description) metaParts.push(item.description);

  const content = (
    <div className="resource-card">
      <div>
        <div className="rtitle">{item.title}</div>
        {metaParts.length > 0 && <div className="rmeta">{metaParts.join(" · ")}</div>}
      </div>
      <span className="rtype">{TYPE_LABEL[item.type] || "Resource"}</span>
    </div>
  );

  if (item.url) {
    return (
      <a href={item.url} target="_blank" rel="noreferrer" style={{ textDecoration: "none", color: "inherit" }}>
        {content}
      </a>
    );
  }
  return content;
}
