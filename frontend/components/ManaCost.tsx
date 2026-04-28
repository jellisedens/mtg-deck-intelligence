const MANA_COLORS: Record<string, string> = {
  W: "bg-mana-white",
  U: "bg-mana-blue",
  B: "bg-mana-black",
  R: "bg-mana-red",
  G: "bg-mana-green",
  C: "bg-mana-colorless",
};

interface Props {
  cost: string | null;
}

export default function ManaCost({ cost }: Props) {
  if (!cost) return null;

  const symbols = cost.match(/\{([^}]+)\}/g) || [];

  return (
    <span className="inline-flex gap-0.5">
      {symbols.map((sym, i) => {
        const value = sym.replace(/[{}]/g, "");
        const colorClass = MANA_COLORS[value];

        if (colorClass) {
          return (
            <span
              key={i}
              className={`w-4 h-4 rounded-full ${colorClass}`}
              title={value}
            />
          );
        }

        // Generic/numeric mana — keep the number
        return (
          <span
            key={i}
            className="w-4 h-4 rounded-full flex items-center justify-center text-xxs font-bold bg-gray-500 text-white"
          >
            {value}
          </span>
        );
      })}
    </span>
  );
}