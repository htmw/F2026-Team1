import torch
import torch.nn as nn
from torchvision.models import resnet50, ResNet50_Weights
# from scripts.resnet_backbone import SharedResNetBackbone


class SharedResNetBackbone(nn.Module):
    """
    Shared ResNet-50 feature extractor for the
    Dual Ocular Disease Screener.

    Input:
        Fundus image: [batch, 3, 512, 512]

    Output:
        Feature vector: [batch, 2048]
    """

    def __init__(self, pretrained=True):
        super().__init__()

        weights = (
            ResNet50_Weights.DEFAULT
            if pretrained
            else None
        )

        model = resnet50(weights=weights)

        # Remove ResNet's original ImageNet
        # classification layer.
        self.features = nn.Sequential(
            *list(model.children())[:-1]
        )

        self.output_features = 2048

    def forward(self, x):
        x = self.features(x)

        # [batch, 2048, 1, 1]
        # ->
        # [batch, 2048]
        x = torch.flatten(x, 1)

        return x


if __name__ == "__main__":

    # Simple verification
    model = SharedResNetBackbone(
        pretrained=False
    )

    sample = torch.randn(
        2, 3, 512, 512
    )

    output = model(sample)

    print("Input shape:", sample.shape)
    print("Output shape:", output.shape)

    assert output.shape == (2, 2048)

    print(
        "Shared ResNet backbone test passed."
    )