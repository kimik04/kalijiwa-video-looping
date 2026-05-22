import shlex


def build_drawtext_filter(layers):
    """Build ffmpeg drawtext filter string from layer definitions.

    Each layer is a dict with keys:
        text, font, fontsize, fontcolor, x, y,
        shadow (bool), shadowcolor, shadowx, shadowy,
        box (bool), boxcolor, boxborderw,
        fade_in_start, fade_in_end, fade_out_start, fade_out_end
    """
    parts = []
    for layer in layers:
        opts = []
        opts.append(f"text='{_escape(layer['text'])}'")
        opts.append(f"font='{layer.get('font', 'Arial')}'")
        opts.append(f"fontsize={layer.get('fontsize', 48)}")
        opts.append(f"fontcolor={layer.get('fontcolor', 'white')}")

        if layer.get('shadow', False):
            sc = layer.get('shadowcolor', 'black@0.6')
            opts.append(f"shadowcolor={sc}")
            opts.append(f"shadowx={layer.get('shadowx', 3)}")
            opts.append(f"shadowy={layer.get('shadowy', 3)}")

        if layer.get('box', False):
            opts.append("box=1")
            opts.append(f"boxcolor={layer.get('boxcolor', 'black@0.5')}")
            opts.append(f"boxborderw={layer.get('boxborderw', 10)}")

        opts.append(f"x={layer.get('x', '(w-text_w)/2')}")
        opts.append(f"y={layer.get('y', '(h-text_h)/2')}")

        alpha = _build_alpha(
            layer.get('fade_in_start', 0),
            layer.get('fade_in_end', 1),
            layer.get('fade_out_start', 6),
            layer.get('fade_out_end', 7),
        )
        opts.append(f"alpha='{alpha}'")

        parts.append("drawtext=" + ":".join(opts))

    return ",".join(parts)


def _escape(text):
    return text.replace("'", "\\'").replace(":", "\\:")


def _build_alpha(fi_start, fi_end, fo_start, fo_end):
    fi_dur = fi_end - fi_start
    fo_dur = fo_end - fo_start
    return (
        f"if(lt(t\\,{fi_start})\\,0\\,"
        f"if(lt(t\\,{fi_end})\\,(t-{fi_start})/{fi_dur}\\,"
        f"if(lt(t\\,{fo_start})\\,1\\,"
        f"if(lt(t\\,{fo_end})\\,1-(t-{fo_start})/{fo_dur}\\,0))))"
    )


def default_layers(channel_name="Musik Jiwo"):
    return [
        {
            "text": channel_name,
            "font": "Avenir Next",
            "fontsize": 80,
            "fontcolor": "white",
            "x": "(w-text_w)/2",
            "y": "(h/2)-100",
            "shadow": True,
            "shadowcolor": "black@0.6",
            "shadowx": 3,
            "shadowy": 3,
            "box": False,
            "fade_in_start": 0.5,
            "fade_in_end": 1.5,
            "fade_out_start": 6,
            "fade_out_end": 7,
        },
        {
            "text": "━━━━━━━━━━━━━━━━━━",
            "font": "Helvetica",
            "fontsize": 16,
            "fontcolor": "white@0.4",
            "x": "(w-text_w)/2",
            "y": "(h/2)-20",
            "shadow": False,
            "box": False,
            "fade_in_start": 1.5,
            "fade_in_end": 2.5,
            "fade_out_start": 6,
            "fade_out_end": 7,
        },
        {
            "text": "  SUBSCRIBE  ",
            "font": "Avenir Next",
            "fontsize": 30,
            "fontcolor": "white",
            "x": "(w-text_w)/2",
            "y": "(h/2)+40",
            "shadow": False,
            "box": True,
            "boxcolor": "red@0.85",
            "boxborderw": 12,
            "fade_in_start": 3,
            "fade_in_end": 4,
            "fade_out_start": 6.5,
            "fade_out_end": 7.5,
        },
        {
            "text": "♥  LIKE",
            "font": "Avenir Next",
            "fontsize": 28,
            "fontcolor": "white",
            "x": "(w-text_w)/2",
            "y": "(h/2)+120",
            "shadow": False,
            "box": True,
            "boxcolor": "0x333333@0.7",
            "boxborderw": 10,
            "fade_in_start": 4.5,
            "fade_in_end": 5.5,
            "fade_out_start": 7,
            "fade_out_end": 8,
        },
    ]
