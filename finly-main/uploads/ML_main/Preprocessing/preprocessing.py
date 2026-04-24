import pandas as pd
import numpy as np
import os
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split 

def load_data(file_path):
    # Load the dataset
    df = pd.read_csv(file_path, sep=';')

    print(df.head())
    print(df.info())
    return df

def missing_values(df):
    # Check for missing values
    missing_values = df.isnull().sum()
    print("Missing values in each column:")
    print(missing_values)

    #hadling missing values
    df = df.dropna()  # Drop rows with missing values
    return df

def convert_datetime(df, date_column):
    #convert date column to datetime format
    df[date_column] = pd.to_datetime(df[date_column], errors='coerce')
    df = df.sort_values(by=date_column)
    df = df.dropna(subset=[date_column])  # Drop rows where date conversion failed
    df = df.set_index(date_column)
    return df

def feature_selection(df, target_column):
    #hanya ambil kolom numerik
    numeric_df = df.select_dtypes(include=[np.number])
    
    if target_column not in numeric_df.columns:
        raise ValueError(f"Target column '{target_column}' is not numeric or does not exist in the dataframe.")
    
    return numeric_df

def scaling_data(df):
    scaler = MinMaxScaler()
    scaled_data = scaler.fit_transform(df)

    scaled_df = pd.DataFrame(scaled_data, columns=df.columns, index=df.index)

    return scaled_df

def split_data(df, target_column, test_size=0.2, random_state=42):
    X = df.drop(columns=[target_column])
    y = df[target_column]

    #time series split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=test_size, random_state=random_state)

    return X_train, X_test, y_train, y_test

def save_preprocessed_data(output_dir,x_train, x_test, y_train, y_test):
    os.makedirs(output_dir, exist_ok=True)
    x_train.to_csv(os.path.join(output_dir, "x_train.csv"), index=False)
    x_test.to_csv(os.path.join(output_dir, "x_test.csv"), index=False)
    y_train.to_csv(os.path.join(output_dir, "y_train.csv"), index=False)
    y_test.to_csv(os.path.join(output_dir, "y_test.csv"), index=False)


#main function

if __name__ == "__main__":

    file_path = r"D:/Financial_Forecast/Data/E-commerce-Sales-Data-main/ecommerce_sales_data.csv"
    output_dir = r"D:/Financial_Forecast/Data/E-commerce-Sales-Data-main/Preprocessed"

    target_column = 'Sales'
    date_column = 'Date'

    df = load_data(file_path)
    df = missing_values(df)
    df = convert_datetime(df, 'Date')
    df = feature_selection(df, target_column)
    df = scaling_data(df)
    x_train, x_test, y_train, y_test = split_data(df, target_column)
    save_preprocessed_data(output_dir, x_train, x_test, y_train, y_test)