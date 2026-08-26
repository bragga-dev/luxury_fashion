
from django.utils.translation import gettext_lazy as _


class ProductSize:
    """Tamanhos de roupa"""
    
    PP = "pp"
    P = "p"
    M = "m"
    G = "g"
    GG = "gg"
    XG = "xg"
    XXG = "xxg"
    XXXG = "xxxg"
    XS = "xs"
    S = "s"
    L = "l"
    XL = "xl"
    XXL = "xxl"
    XXXL = "xxxl"
    XXXXL = "xxxxl"
    UNIQUE = "unique"
    
    CHOICES = [
        (PP, _("PP")),
        (P, _("P")),
        (M, _("M")),
        (G, _("G")),
        (GG, _("GG")),
        (XG, _("XG")),
        (XXG, _("XXG")),
        (XXXG, _("XXXG")),
        (XS, _("XS")),
        (S, _("S")),
        (L, _("L")),
        (XL, _("XL")),
        (XXL, _("XXL")),
        (XXXL, _("XXXL")),
        (XXXXL, _("XXXXL")),
        (UNIQUE, _("Único")),
    ]
    
    # Ordem de classificação (do menor para o maior)
    ORDER = {
        PP: 1,
        P: 2,
        XS: 3,
        S: 4,
        M: 5,
        L: 6,
        XL: 7,
        G: 8,
        GG: 9,
        XG: 10,
        XXL: 11,
        XXG: 12,
        XXXL: 13,
        XXXG: 14,
        XXXXL: 15,
        UNIQUE: 0,
    }
    
    # Cores associadas a cada tamanho (para visualização)
    COLORS = {
        PP: "#FF69B4",  # Rosa
        P: "#FF6B6B",   # Vermelho claro
        M: "#4ECDC4",   # Turquesa
        G: "#45B7D1",   # Azul
        GG: "#96CEB4",  # Verde
        XG: "#FFEAA7",  # Amarelo
        XXG: "#DDA0DD", # Ameixa
        XXXG: "#F0E68C", # Caqui
        XS: "#FF9FF3",  # Rosa claro
        S: "#54A0FF",   # Azul claro
        L: "#5F27CD",   # Roxo
        XL: "#FF6F91",  # Rosa
        XXL: "#FF9671", # Laranja
        XXXL: "#FFC75F", # Amarelo
        XXXXL: "#F9F871", # Amarelo claro
        UNIQUE: "#808080", # Cinza
    }


class ProductColor:
    """Cores de roupa"""
    
    WHITE = "white"
    BLACK = "black"
    RED = "red"
    BLUE = "blue"
    GREEN = "green"
    YELLOW = "yellow"
    ORANGE = "orange"
    PURPLE = "purple"
    PINK = "pink"
    BROWN = "brown"
    GRAY = "gray"
    BEIGE = "beige"
    NAVY = "navy"
    MAROON = "maroon"
    OLIVE = "olive"
    TEAL = "teal"
    CORAL = "coral"
    GOLD = "gold"
    SILVER = "silver"
    MULTICOLOR = "multicolor"
    OTHER = "other"
    
    CHOICES = [
        (WHITE, _("Branco")),
        (BLACK, _("Preto")),
        (RED, _("Vermelho")),
        (BLUE, _("Azul")),
        (GREEN, _("Verde")),
        (YELLOW, _("Amarelo")),
        (ORANGE, _("Laranja")),
        (PURPLE, _("Roxo")),
        (PINK, _("Rosa")),
        (BROWN, _("Marrom")),
        (GRAY, _("Cinza")),
        (BEIGE, _("Bege")),
        (NAVY, _("Azul Marinho")),
        (MAROON, _("Bordô")),
        (OLIVE, _("Oliva")),
        (TEAL, _("Azul Esverdeado")),
        (CORAL, _("Coral")),
        (GOLD, _("Dourado")),
        (SILVER, _("Prata")),
        (MULTICOLOR, _("Multicolor")),
        (OTHER, _("Outra")),
    ]
    
    # Cores em hexadecimal para exibição
    HEX_COLORS = {
        WHITE: "#FFFFFF",
        BLACK: "#000000",
        RED: "#FF0000",
        BLUE: "#0000FF",
        GREEN: "#00FF00",
        YELLOW: "#FFFF00",
        ORANGE: "#FFA500",
        PURPLE: "#800080",
        PINK: "#FFC0CB",
        BROWN: "#A52A2A",
        GRAY: "#808080",
        BEIGE: "#F5F5DC",
        NAVY: "#000080",
        MAROON: "#800000",
        OLIVE: "#808000",
        TEAL: "#008080",
        CORAL: "#FF7F50",
        GOLD: "#FFD700",
        SILVER: "#C0C0C0",
        MULTICOLOR: "#FF1493",
        OTHER: "#D3D3D3",
    }
    
    # Cores legíveis para texto (preto ou branco)
    TEXT_COLORS = {
        WHITE: "black",
        BLACK: "white",
        RED: "white",
        BLUE: "white",
        GREEN: "white",
        YELLOW: "black",
        ORANGE: "black",
        PURPLE: "white",
        PINK: "black",
        BROWN: "white",
        GRAY: "black",
        BEIGE: "black",
        NAVY: "white",
        MAROON: "white",
        OLIVE: "white",
        TEAL: "white",
        CORAL: "black",
        GOLD: "black",
        SILVER: "black",
        MULTICOLOR: "black",
        OTHER: "black",
    }
    
    # Emojis para cores (para visualização rápida)
    EMOJIS = {
        WHITE: "⬜",
        BLACK: "⬛",
        RED: "🟥",
        BLUE: "🟦",
        GREEN: "🟩",
        YELLOW: "🟨",
        ORANGE: "🟧",
        PURPLE: "🟪",
        PINK: "💗",
        BROWN: "🟫",
        GRAY: "⬜",
        BEIGE: "🟫",
        NAVY: "🔵",
        MAROON: "🟥",
        OLIVE: "🟩",
        TEAL: "🟦",
        CORAL: "🟧",
        GOLD: "⭐",
        SILVER: "⚪",
        MULTICOLOR: "🌈",
        OTHER: "🎨",
    }