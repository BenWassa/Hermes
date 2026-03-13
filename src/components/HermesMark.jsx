import detailedMark from '../assets/hermes-caduceus-detailed.svg';
import hudMark from '../assets/hermes-caduceus-hud.svg';

export const HERMES_MARK_VARIANTS = {
  detailed: detailedMark,
  hud: hudMark
};

const ACTIVE_VARIANT = 'detailed';

export function HermesMark({ className = 'h-10 w-10', variant = ACTIVE_VARIANT }) {
  const src = HERMES_MARK_VARIANTS[variant] || HERMES_MARK_VARIANTS.detailed;

  return <img src={src} alt="" aria-hidden="true" className={className} />;
}
