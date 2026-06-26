/**
 * Shared placeholder for screens whose full CRUD lands in later E1/E2/E3
 * tasks. Keeps the skeleton navigable and the build green.
 */
export function ScreenStub({
  title,
  description,
  task,
}: {
  title: string;
  description: string;
  task: string;
}) {
  return (
    <section>
      <h1 style={{ margin: "0 0 8px", fontSize: 24 }}>{title}</h1>
      <p style={{ color: "var(--mg-muted)", margin: "0 0 20px", maxWidth: 640 }}>
        {description}
      </p>
      <div
        style={{
          border: "1px dashed var(--mg-border)",
          borderRadius: 8,
          padding: "32px 24px",
          background: "var(--mg-surface)",
          color: "var(--mg-muted)",
          fontSize: 14,
        }}
      >
        Screen scaffold — full functionality lands in {task}.
      </div>
    </section>
  );
}
