import keras
import keras_hub
import tensorflow as tf

# re-create the BERT preprocessor and backbones since we don't save these as part of the model
preprocessor = keras_hub.models.BertTextClassifierPreprocessor.from_preset(
    "bert_base_en_uncased",
    sequence_length=512,
)

# build preprocessor before FastAPI receives requests
preprocessor(
    tf.constant(
        ["lorem ipsum"]
    )
)

backbone = keras_hub.models.BertBackbone.from_preset(
    "bert_base_en_uncased"
)

backbone.trainable = False

token_input = keras.Input(
    shape=(512,),
    dtype="int32",
    name="token_ids"
)

segment_input = keras.Input(
    shape=(512,),
    dtype="int32",
    name="segment_ids"
)

mask_input = keras.Input(
    shape=(512,),
    dtype="int32",
    name="padding_mask"
)

outputs = backbone({
    "token_ids": token_input,
    "segment_ids": segment_input,
    "padding_mask": mask_input
})

embedding_model = keras.Model(
    inputs=[
        token_input,
        segment_input,
        mask_input
    ],
    outputs=outputs["pooled_output"]
)