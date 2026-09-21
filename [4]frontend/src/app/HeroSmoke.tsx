type HeroSmokeProps = {
  left: string;
  top: string;
};

const delays = ["0s", "1.5s", "3s", "4.5s"];

export default function HeroSmoke({ left, top }: HeroSmokeProps) {
  return (
    <div
      aria-hidden="true"
      data-testid="hero-smoke"
      className="pointer-events-none absolute z-20 h-10 w-10"
      style={{ left, top }}
    >
      {delays.map((delay) => (
        <span
          key={delay}
          className="animate-smoke absolute inset-0 block h-10 w-10 rounded-full bg-gray-300/40 blur-md"
          style={{ animationDelay: delay }}
        />
      ))}
    </div>
  );
}
