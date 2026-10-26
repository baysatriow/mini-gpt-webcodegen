import type { BuiltInParserName, Plugin } from "prettier";
import type { SourceFilename } from "@/lib/api-types";

type FormatterAssets = {
  format: (source: string, options: {
    parser: BuiltInParserName;
    plugins: Plugin[];
    printWidth: number;
    tabWidth: number;
    semi: boolean;
    singleQuote: boolean;
    htmlWhitespaceSensitivity: "css";
  }) => Promise<string>;
  plugins: Plugin[];
  parser: BuiltInParserName;
};

async function loadFormatter(filename: SourceFilename): Promise<FormatterAssets> {
  const prettier = await import("prettier/standalone");

  if (filename === "index.html") {
    const html = await import("prettier/plugins/html");
    return { format: prettier.format, plugins: [html], parser: "html" };
  }

  if (filename === "styles.css") {
    const postcss = await import("prettier/plugins/postcss");
    return { format: prettier.format, plugins: [postcss], parser: "css" };
  }

  const [babel, estree] = await Promise.all([
    import("prettier/plugins/babel"),
    import("prettier/plugins/estree"),
  ]);
  return { format: prettier.format, plugins: [babel, estree], parser: "babel" };
}

export async function formatSourceCode(filename: SourceFilename, source: string): Promise<string> {
  if (!( ["index.html", "styles.css", "app.js"] as string[]).includes(filename)) {
    throw new Error("Unsupported source file");
  }

  if (!source.trim()) return source;

  const formatter = await loadFormatter(filename);
  return formatter.format(source, {
    parser: formatter.parser,
    plugins: formatter.plugins,
    printWidth: 100,
    tabWidth: 2,
    semi: true,
    singleQuote: true,
    htmlWhitespaceSensitivity: "css",
  });
}
