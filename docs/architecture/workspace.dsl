workspace "py-doc" "The C4 model of py-doc, the Markdown technical documentation toolset." {

    !identifiers hierarchical

    model {
        author = person "Author" "Writes technical documentation in Markdown and builds it into Word, PowerPoint, PDF, HTML and web sites."
        reader = person "Reader" "Reads the documents and sites that py-doc builds."

        ci = softwareSystem "CI pipeline" "Runs the same build and lint commands on every change, such as GitHub Actions." "External"
        registries = softwareSystem "Package registries" "Docker Hub, GitHub releases, PyPI and npm: where the tool image and site builds download their tools." "External"
        office = softwareSystem "Word and PowerPoint" "Open the built documents and decks, and are where documents start before py-doc imports them." "External"

        pydoc = softwareSystem "py-doc" "Turns Markdown into Word, PowerPoint, PDF, HTML and web sites, checks the writing, and documents C4 models." {
            cli = container "py-doc command" "The py-doc command and Python package. Reads py-doc.yml, prepares the Markdown and starts every tool in the tool image." "Python 3.10+" {
                commands = component "Commands" "Parses the command line and hands each command to its module: build, docx, slides, poster, lint, check, generate, stats, diff, c4, site, import, init, new, template, tools, doctor, setup, migrate. Runs the build pipeline around the documents." "argparse"
                configuration = component "Configuration" "Loads py-doc.yml and checks every key, so a mistake is an error that names its place." "PyYAML"
                pipeline = component "Build pipeline" "Joins a document's sources, expands includes, conditions and variables, and picks the template and the output name." "Python"
                diagrams = component "Diagram renderer" "Turns diagram fences, poster blocks, plots and the written forms of specialist fences into pictures with the right tool, and keeps them in a cache." "Python"
                posters = component "Poster builder" "Makes a self-contained HTML poster from Markdown: its layout, themes, fonts, maths and native blocks, drawn as SVG and HTML." "Python, segno, latex2mathml"
                diagramCli = component "Image command" "py-doc diagram and render_diagram(): draw one diagram, poster block or plot as an SVG, PNG, WebP or PDF file, or every one of a Markdown file." "Python"
                pandocEngine = component "Pandoc engine" "Runs pandoc with py-doc's Lua filters, then finishes Word and PowerPoint files: templates, placeholders, captions, footers." "pandoc, Lua, python-docx, python-pptx"
                c4 = component "C4 integration" "Reads Structurizr workspaces, writes chapters from the model, draws the views and runs the live editor." "structurizr-cli, Structurizr Local"
                linter = component "Linter" "Checks the writing with the built-in rules, structure rules, markdownlint and Vale, and reports one list." "markdown-it-py, Vale"
                importers = component "Importers" "Turn Word documents and PowerPoint decks into Markdown that builds again." "python-docx, python-pptx"
                site = component "Site generator" "Writes a page per source file and the navigation for MkDocs or Astro + Starlight, then builds the site." "pandoc, MkDocs, Astro"
                scaffold = component "Project scaffold" "Starts a new project: py-doc.yml, a first document, a C4 model, templates and a site." "Python"
                runner = component "Tool runner" "Starts a program in a fresh container as the calling user, with only the folders it needs, and reports its whole output when it fails." "Docker CLI, WSL"
                generators = component "Content generators" "Write Markdown from other sources before the build: glossaries, indexes, traceability, API references, diagram files, commands." "Python, entry points"
                analysis = component "Analysis" "Counts what documents hold, checks a project without building it, and compares versions by section." "Python, Git"
                report = component "Build report" "Records the tools, sources, outputs, diagrams and warnings of a build as JSON." "JSON schema"
                watch = component "Live preview" "With --watch, builds documents, decks and posters again on every save, writes an HTML twin of each document and deck, and serves the pages on 127.0.0.1 with a script that reloads them." "Python, http.server"
            }
            toolImage = container "Tool image" "Every program that is not Python: pandoc, XeLaTeX, PlantUML, Mermaid, Graphviz, the diagram tools, Chromium, structurizr-cli, Vale, markdownlint, MkDocs and Node." "Docker image on Debian 12"
            scienceImage = container "Science image" "Optional: the tool image with the scientific libraries some fences need, such as RDKit, matplotlib and CoolProp. Built the first time a fence needs it." "Docker image on the tool image"
            vscode = container "VS Code extension" "Starts the live preview (--watch) of the open file with the right command and shows it beside the editor. It draws no block itself." "JavaScript, js-yaml"
            local = container "Structurizr Local" "Shows a workspace in a browser to view it and arrange its views, and draws the pictures for documents." "Docker image structurizr/structurizr"
            cache = container "Caches" "Diagram pictures (user cache folder), Structurizr exports, generated chapters and live preview pages (.py-doc in the project)." "Files" "Store"
        }

        author -> pydoc.cli.commands "Runs py-doc commands" "Terminal"
        author -> pydoc.local "Views the model and arranges its views" "Browser, HTTP"
        reader -> office "Opens the documents in"
        author -> pydoc.vscode "Writes and previews documents in" "VS Code"
        pydoc.vscode -> pydoc.cli.commands "Starts py-doc docx, slides or poster --watch for the open file" "Child process"
        pydoc.vscode -> pydoc.cli.watch "Shows the served preview from" "HTTP on 127.0.0.1"
        pydoc.cli.commands -> pydoc.cli.watch "Runs --watch with"
        pydoc.cli.watch -> pydoc.cli.pipeline "Builds each document and its HTML twin with"
        pydoc.cli.watch -> pydoc.cache "Keeps the HTML twins in" "Files"
        ci -> pydoc.cli.commands "Runs builds and lint checks" "Shell"
        pydoc.cli.commands -> pydoc.cli.configuration "Loads the project from"
        pydoc.cli.commands -> pydoc.cli.pipeline "Builds documents with"
        pydoc.cli.commands -> pydoc.cli.linter "Checks the writing with"
        pydoc.cli.commands -> pydoc.cli.importers "Imports files with"
        pydoc.cli.commands -> pydoc.cli.site "Makes sites with"
        pydoc.cli.commands -> pydoc.cli.scaffold "Starts projects with"
        pydoc.cli.commands -> pydoc.cli.c4 "Checks, exports and edits models with"
        pydoc.cli.commands -> pydoc.cli.generators "Runs the content generators with"
        pydoc.cli.commands -> pydoc.cli.analysis "Counts, checks and compares documents with"
        pydoc.cli.analysis -> pydoc.cli.linter "Lints the sources with"
        pydoc.cli.site -> pydoc.cli.generators "Runs the content generators first with"
        pydoc.cli.pipeline -> pydoc.cli.c4 "Asks for the chapters of a structurizr source"
        pydoc.cli.pipeline -> pydoc.cli.diagrams "Has the diagrams drawn by"
        pydoc.cli.pipeline -> pydoc.cli.pandocEngine "Has each output written by"
        pydoc.cli.pipeline -> pydoc.cli.report "Records what it built in"
        pydoc.cli.site -> pydoc.cli.pipeline "Prepares each page with"
        pydoc.cli.site -> pydoc.cli.diagrams "Has the diagrams drawn as SVG by"
        pydoc.cli.site -> pydoc.cli.runner "Runs pandoc, MkDocs and Astro through"
        pydoc.cli.scaffold -> pydoc.cli.site "Makes the site project with"
        pydoc.cli.diagrams -> pydoc.cli.runner "Runs the diagram tools through"
        pydoc.cli.diagrams -> pydoc.cache "Keeps pictures in" "Files"
        pydoc.cli.pandocEngine -> pydoc.cli.runner "Runs pandoc and XeLaTeX through"
        pydoc.cli.c4 -> pydoc.cli.runner "Runs structurizr-cli and Chromium through"
        pydoc.cli.c4 -> pydoc.local "Starts, and has the views drawn by" "Docker, HTTP"
        pydoc.cli.c4 -> pydoc.cache "Keeps exports and chapters in" "Files"
        pydoc.cli.linter -> pydoc.cli.runner "Runs markdownlint and Vale through"
        pydoc.cli.importers -> pydoc.cli.runner "Converts EMF and WMF pictures through"
        pydoc.cli.runner -> pydoc.toolImage "Starts a container of" "Docker Engine, WSL 2 on Windows"
        pydoc.cli.runner -> pydoc.scienceImage "Starts a container of, for a scientific fence, building it first" "Docker Engine, WSL 2 on Windows"
        pydoc.scienceImage -> pydoc.toolImage "Is built on"
        pydoc.cli.commands -> pydoc.cli.posters "Builds posters with"
        pydoc.cli.commands -> pydoc.cli.diagramCli "Draws image files with"
        pydoc.cli.posters -> pydoc.cli.diagrams "Has its diagram fences and plots drawn by"
        pydoc.cli.posters -> pydoc.cli.runner "Prints its PDF with Chromium through"
        pydoc.cli.diagrams -> pydoc.cli.posters "Draws poster blocks in documents with"
        pydoc.cli.diagramCli -> pydoc.cli.diagrams "Draws with"
        pydoc.cli.watch -> pydoc.cli.posters "Builds each poster with"
        pydoc.toolImage -> pydoc.local "Opens the diagrams in headless Chromium" "HTTP on the shared network"
        pydoc.toolImage -> registries "Is built from, and site builds download from" "HTTPS"
        pydoc.cli.pandocEngine -> office "Writes files for" ".docx, .pptx"

        live = deploymentEnvironment "Workstation" {
            deploymentNode "Windows 11 or Linux" "The author's computer." "Windows 11, Ubuntu, Debian" {
                deploymentNode "Python" "The py-doc package, installed with pip." "Python 3.10+" {
                    containerInstance pydoc.cli
                }
                deploymentNode "Visual Studio Code" "The author's editor, with the py-doc extension installed from editors/vscode." "VS Code 1.75+" {
                    containerInstance pydoc.vscode
                }
                deploymentNode "Cache folders" "The user cache folder and the project's .py-doc folder." "File system" {
                    containerInstance pydoc.cache
                }
                deploymentNode "WSL 2 distro" "On Windows only: Docker Engine runs in Ubuntu or Debian under WSL 2. On Linux this level is not there." "Ubuntu, Debian" {
                    deploymentNode "Docker Engine" "Runs every tool in a fresh container." "Docker Engine 27+" {
                        containerInstance pydoc.toolImage
                        containerInstance pydoc.scienceImage
                        containerInstance pydoc.local
                    }
                }
            }
        }
    }

    views {
        systemContext pydoc "SystemContext" "py-doc, the people who use it and the systems around it." {
            include *
            autoLayout lr
        }
        container pydoc "Containers" "What py-doc is made of, and where its tools run." {
            include *
            autoLayout lr
        }
        component pydoc.cli "Components" "The modules of the py-doc command." {
            include *
            autoLayout tb
        }
        dynamic pydoc.cli "Build" "How py-doc build makes one Word document." {
            author -> pydoc.cli.commands "py-doc build guide"
            pydoc.cli.commands -> pydoc.cli.configuration "Loads py-doc.yml"
            pydoc.cli.commands -> pydoc.cli.pipeline "Builds the guide"
            pydoc.cli.pipeline -> pydoc.cli.diagrams "Draws the diagram fences"
            pydoc.cli.diagrams -> pydoc.cli.runner "Runs PlantUML, Mermaid and the rest"
            pydoc.cli.pipeline -> pydoc.cli.pandocEngine "Writes the Word file"
            pydoc.cli.pandocEngine -> pydoc.cli.runner "Runs pandoc"
            pydoc.cli.pipeline -> pydoc.cli.report "Records the outputs"
            autoLayout lr
        }
        dynamic pydoc.cli "LivePreview" "How the VS Code extension shows a live preview of a Word document." {
            author -> pydoc.vscode "Clicks the eye button"
            pydoc.vscode -> pydoc.cli.commands "py-doc docx guide.md --watch"
            pydoc.cli.commands -> pydoc.cli.watch "Watches guide.md"
            pydoc.cli.watch -> pydoc.cli.pipeline "Builds guide.docx and its HTML twin"
            pydoc.cli.watch -> pydoc.cache "Writes the twin to .py-doc/preview"
            pydoc.vscode -> pydoc.cli.watch "Shows the twin, which reloads on every save"
            autoLayout lr
        }
        deployment pydoc live "Deployment" "Where py-doc runs on an author's computer." {
            include *
            autoLayout lr
        }
        styles {
            element "Person" {
                shape person
                background #0b4f8a
                color #ffffff
            }
            element "Software System" {
                background #1168bd
                color #ffffff
            }
            element "External" {
                background #8a8a8a
                color #ffffff
            }
            element "Container" {
                background #438dd5
                color #ffffff
            }
            element "Component" {
                background #85bbf0
                color #000000
            }
            element "Store" {
                shape cylinder
            }
        }
    }
}
