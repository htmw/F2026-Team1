import torch
import torch.nn as nn

from resnet_backbone import SharedResNetBackbone


class GlaucomaNet(nn.Module):
    """
    Glaucoma-only model for Task 11 ablation.

    Uses the same ResNet-50 backbone as DualNet,
    but has only one binary classification head.

    Input:
        Fundus images: [batch, 3, 512, 512]

    Output:
        Glaucoma logits: [batch, 1]
    """

    def __init__(self, pretrained=True):
        super().__init__()

        # Same ResNet-50 backbone used by the DUAL model.
        self.backbone = SharedResNetBackbone(
            pretrained=pretrained
        )

        # Glaucoma-only binary classification head.
        self.glaucoma_head = nn.Linear(
            self.backbone.output_features,
            1
        )

    def forward(self, x):
        features = self.backbone(x)
        glaucoma_logits = self.glaucoma_head(features)

        return glaucoma_logits


if __name__ == "__main__":
    # Architecture test only.
    model = GlaucomaNet(pretrained=False)

    sample = torch.randn(
        2, 3, 512, 512
    )

    glaucoma_output = model(sample)

    print("Input shape:", sample.shape)
    print("Glaucoma output shape:", glaucoma_output.shape)

    assert glaucoma_output.shape == (2, 1)

    print("Glaucoma-only model test passed.")