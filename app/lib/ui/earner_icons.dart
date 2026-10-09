/// The PC bar's earner icons, so the phone reads the same at a glance.
library;

const Map<String, String> _icons = {
  'workout': '💪',
  'leetcode': '🧩',
  'reading': '📖',
  'anki': '🗂',
  'automation': '⚙',
};

/// The icon for earner [name], or a bullet for one the phone does not know.
String earnerIcon(String name) => _icons[name] ?? '•';

/// The shutdown marker. The PC bar uses ⏻ (U+23FB), but Android ships no glyph
/// for it -- on the phone it renders as an empty box, in the app and in the
/// widget -- so the phone uses the emoji-font plug instead.
const String kShutdownIcon = '🔌';
