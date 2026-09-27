import torch
import torch.nn as nn

from resnet_backbone import SharedResNetBackbone


class DualNet(nn.Module):
    """
    Shared-backbone DUAL model for cataract and glaucoma.

    Input:
        Fundus images: [batch, 3, 512, 512]

    Output:
        Cataract logits: [batch, 1]
        Glaucoma logits: [batch, 1]
    """

    def __init__(self, pretrained=True):
        super().__init__()

        # One shared ResNet-50 backbone.
        self.backbone = SharedResNetBackbone(
            pretrained=pretrained
        )

        # Separate binary classification head for cataract.
        self.cataract_head = nn.Linear(
            self.backbone.output_features,
            1
        )

        # Separate binary classification head for glaucoma.
        self.glaucoma_head = nn.Linear(
            self.backbone.output_features,
            1
        )

    def forward(self, x):
        # Shared features for both disease tasks.
        features = self.backbone(x)

        cataract_logits = self.cataract_head(features)
        glaucoma_logits = self.glaucoma_head(features)

        return cataract_logits, glaucoma_logits


if __name__ == "__main__":
    # Architecture test only.
    # No ImageNet download is needed for this shape check.
    model = DualNet(pretrained=False)

    sample = torch.randn(
        2, 3, 512, 512
    )

    cataract_output, glaucoma_output = model(sample)

    print("Input shape:", sample.shape)
    print("Cataract output shape:", cataract_output.shape)
    print("Glaucoma output shape:", glaucoma_output.shape)

    assert cataract_output.shape == (2, 1)
    assert glaucoma_output.shape == (2, 1)

    print("DUAL model test passed.")