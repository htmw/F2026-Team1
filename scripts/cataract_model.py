import torch.nn as nn

from resnet_backbone import SharedResNetBackbone


class CataractOnlyNet(nn.Module):
    """
    Cataract-only ablation model for Task 11.

    Uses the same shared ResNet-50 backbone defined
    for the DUAL model, with a single binary
    cataract classification head.
    """

    def __init__(self, pretrained=True):
        super().__init__()

        self.backbone = SharedResNetBackbone(
            pretrained=pretrained
        )

        self.cataract_head = nn.Linear(
            self.backbone.output_features,
            1
        )

    def forward(self, x):
        features = self.backbone(x)
        cataract_logits = self.cataract_head(features)

        return cataract_logits