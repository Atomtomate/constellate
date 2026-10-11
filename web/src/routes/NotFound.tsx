/** Reached for any path this shell does not route -- including a stale deep link. */
export function NotFound() {
  return (
    <section>
      <h2>Not found</h2>
      <p>There is nothing at this address.</p>
    </section>
  );
}
