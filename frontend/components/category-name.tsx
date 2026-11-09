import { categoryLabel, type Category } from "@/lib/categories";

export function CategoryName({
  id,
  categories,
  empty,
}: Readonly<{ id: string | null; categories?: Category[]; empty?: string }>) {
  const name = categories?.find(
    (category) => category.category_id === id && category.name,
  )?.name;
  return (
    <div>
      <span>{categoryLabel(id, categories, empty)}</span>
      {id && name ? (
        <span className="mt-1 block text-xs text-[var(--muted)]">{id}</span>
      ) : null}
    </div>
  );
}
