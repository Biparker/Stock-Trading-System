"""Feature selector for user-driven feature choice."""

import pandas as pd
from config import AVAILABLE_FEATURES


class FeatureSelector:
    """Interactive feature selector for time-series analysis."""

    def __init__(self, data):
        self.data = data
        self.selected_features = []

    def display_available_features(self):
        """Display available features to the user."""
        print("\n" + "="*60)
        print("AVAILABLE FEATURES FOR TIME-SERIES ANALYSIS")
        print("="*60)
        print("\nTarget Variable (always included):")
        print("  1. Close Price - Daily closing stock price (required)")

        print("\nOptional Features:")
        idx = 2
        for key, description in AVAILABLE_FEATURES.items():
            if key != 'close':
                print(f"  {idx}. {description}")
                idx += 1

        print("\n" + "="*60)

    def engineer_features(self):
        """Create engineered features from raw data."""
        df = self.data.copy()

        # Price range
        df['price_range'] = df['high'] - df['low']

        # Daily price change %
        df['price_change_pct'] = df['close'].pct_change() * 100

        # Volume moving average (20-day)
        df['volume_ma'] = df['volume'].rolling(window=20).mean()

        return df

    def select_features_interactive(self):
        """
        Allow user to interactively select features.

        Returns:
            list: Selected feature columns
        """
        # Engineer features first
        data = self.engineer_features()

        # Close price is always included
        self.selected_features = ['close']

        self.display_available_features()

        print("\nSelect features to include in analysis:")
        print("(Enter feature numbers separated by commas, e.g., '2,3,5')")
        print("(Press Enter to use default: close price only)")

        user_input = input("\nYour choice: ").strip()

        if not user_input:
            print("\nUsing default: Close Price only")
            return self.selected_features

        try:
            indices = [int(x.strip()) for x in user_input.split(',')]
            feature_map = {1: 'close'}
            idx = 2
            for key in AVAILABLE_FEATURES.keys():
                if key != 'close':
                    feature_map[idx] = key
                    idx += 1

            for idx in indices:
                if idx in feature_map:
                    feat = feature_map[idx]
                    if feat not in self.selected_features:
                        self.selected_features.append(feat)
                else:
                    print(f"⚠️  Warning: Invalid choice {idx}, skipping")

        except ValueError:
            print("⚠️  Invalid input. Using default: Close Price only")
            self.selected_features = ['close']

        # Validate features exist
        self.selected_features = [f for f in self.selected_features if f in data.columns]

        print(f"\nSelected features: {', '.join(self.selected_features)}")

        return self.selected_features

    def select_features_programmatic(self, feature_list):
        """
        Select features programmatically.

        Args:
            feature_list (list): List of feature names to select

        Returns:
            list: Validated selected features
        """
        data = self.engineer_features()

        self.selected_features = []

        # Handle None or empty list
        if feature_list is None:
            feature_list = ['close']

        for feat in feature_list:
            if feat in data.columns:
                if feat not in self.selected_features:
                    self.selected_features.append(feat)
            else:
                print(f"⚠️  Feature '{feat}' not found in data")

        # Ensure close price is included
        if 'close' not in self.selected_features:
            self.selected_features.insert(0, 'close')

        return self.selected_features

    def get_selected_data(self, interactive=True, feature_list=None):
        """
        Get data with only selected features.

        Args:
            interactive (bool): Use interactive selection or programmatic
            feature_list (list): Features to select (if interactive=False)

        Returns:
            pd.DataFrame: Data with selected features only
        """
        if interactive:
            self.select_features_interactive()
        else:
            # If no features specified, use close price only
            if feature_list is None:
                feature_list = ['close']
            self.select_features_programmatic(feature_list)

        data = self.engineer_features()
        return data[['date'] + self.selected_features]
